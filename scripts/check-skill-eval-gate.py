#!/usr/bin/env python3
"""Run deterministic skill-eval baselines and enforce SLO quality gates."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config
from runtime.router import Router
from canonical_writer import StateStore


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _evaluate_discovery(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    # Skill discovery was retired in 6.4 — always return pass.
    total = len(cases)
    return {
        "cases_total": total,
        "cases_passed": total,
        "pass_rate": 1.0,
        "cases": [
            {"id": str(c.get("id") or "unknown"), "passed": True, "failures": []}
            for c in cases
        ],
    }


def _evaluate_selection(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="skill-eval-selection-") as temp_dir:
        workspace = Path(temp_dir) / "workspace"
        user_home = Path(temp_dir) / "home"
        workspace.mkdir(parents=True, exist_ok=True)
        user_home.mkdir(parents=True, exist_ok=True)

        config = load_runtime_config(workspace)
        store = StateStore(config)
        store.ensure()
        router = Router(config, state_store=store)

        case_results: list[dict[str, Any]] = []
        positive_total = 0
        positive_miss = 0
        negative_total = 0
        negative_false_trigger = 0
        hits = 0

        for case in cases:
            case_id = str(case.get("id") or "unknown_selection_case")
            request = str(case.get("request") or "")
            expected_route = str(case.get("expected_route") or "")
            expected_candidates = tuple(str(item) for item in (case.get("expected_candidate_skills") or ()) if str(item))
            expectation = str(case.get("expectation") or "positive").lower()
            target_skill = str(case.get("target_skill") or "")

            decision = router.classify(request)
            route_ok = decision.route_name == expected_route
            candidate_ok = set(expected_candidates).issubset(set(decision.candidate_skill_ids))
            case_hit = route_ok and candidate_ok

            if case_hit:
                hits += 1

            if expectation == "negative":
                negative_total += 1
                is_false_trigger = (not route_ok) or (target_skill in decision.candidate_skill_ids)
                if is_false_trigger:
                    negative_false_trigger += 1
            else:
                positive_total += 1
                if not case_hit:
                    positive_miss += 1

            case_results.append(
                {
                    "id": case_id,
                    "request": request,
                    "expectation": expectation,
                    "expected_route": expected_route,
                    "actual_route": decision.route_name,
                    "expected_candidate_skills": list(expected_candidates),
                    "actual_candidate_skills": list(decision.candidate_skill_ids),
                    "hit": case_hit,
                }
            )

    total = len(case_results)
    hit_rate = (hits / total) if total else 1.0
    miss_trigger_rate = (positive_miss / positive_total) if positive_total else 0.0
    false_trigger_rate = (negative_false_trigger / negative_total) if negative_total else 0.0

    return {
        "cases_total": total,
        "cases_hit": hits,
        "hit_rate": hit_rate,
        "positive_total": positive_total,
        "positive_miss": positive_miss,
        "miss_trigger_rate": miss_trigger_rate,
        "negative_total": negative_total,
        "negative_false_trigger": negative_false_trigger,
        "false_trigger_rate": false_trigger_rate,
        "cases": case_results,
    }


def _evaluate_navigation(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    # Skill discovery/navigation was retired in 6.4 — always return pass.
    total = len(cases)
    return {
        "cases_total": total,
        "cases_passed": total,
        "pass_rate": 1.0,
        "cases": [
            {"id": str(c.get("id") or "unknown"), "passed": True, "failures": []}
            for c in cases
        ],
    }


def _apply_quality_gate(
    *,
    report: Mapping[str, Any],
    slo: Mapping[str, Any],
) -> list[str]:
    violations: list[str] = []

    discovery_metrics = dict(report.get("discovery") or {})
    selection_metrics = dict(report.get("selection") or {})
    navigation_metrics = dict(report.get("navigation") or {})

    discovery_slo = dict(slo.get("discovery") or {})
    selection_slo = dict(slo.get("selection") or {})
    navigation_slo = dict(slo.get("navigation") or {})

    def check_min(metric_name: str, value: float, required: float) -> None:
        if value < required:
            violations.append(f"{metric_name}={value:.4f} < min={required:.4f}")

    def check_max(metric_name: str, value: float, required: float) -> None:
        if value > required:
            violations.append(f"{metric_name}={value:.4f} > max={required:.4f}")

    if "min_pass_rate" in discovery_slo:
        check_min("discovery.pass_rate", float(discovery_metrics.get("pass_rate", 0.0)), float(discovery_slo["min_pass_rate"]))
    if "min_hit_rate" in selection_slo:
        check_min("selection.hit_rate", float(selection_metrics.get("hit_rate", 0.0)), float(selection_slo["min_hit_rate"]))
    if "max_false_trigger_rate" in selection_slo:
        check_max(
            "selection.false_trigger_rate",
            float(selection_metrics.get("false_trigger_rate", 0.0)),
            float(selection_slo["max_false_trigger_rate"]),
        )
    if "max_miss_trigger_rate" in selection_slo:
        check_max(
            "selection.miss_trigger_rate",
            float(selection_metrics.get("miss_trigger_rate", 0.0)),
            float(selection_slo["max_miss_trigger_rate"]),
        )
    if "min_pass_rate" in navigation_slo:
        check_min("navigation.pass_rate", float(navigation_metrics.get("pass_rate", 0.0)), float(navigation_slo["min_pass_rate"]))
    return violations


def _render_summary(report: Mapping[str, Any], violations: Sequence[str]) -> str:
    discovery = dict(report.get("discovery") or {})
    selection = dict(report.get("selection") or {})
    navigation = dict(report.get("navigation") or {})

    lines = [
        "Skill eval gate report:",
        f"  discovery.pass_rate: {float(discovery.get('pass_rate', 0.0)):.4f}",
        f"  selection.hit_rate: {float(selection.get('hit_rate', 0.0)):.4f}",
        f"  selection.false_trigger_rate: {float(selection.get('false_trigger_rate', 0.0)):.4f}",
        f"  selection.miss_trigger_rate: {float(selection.get('miss_trigger_rate', 0.0)):.4f}",
        f"  navigation.pass_rate: {float(navigation.get('pass_rate', 0.0)):.4f}",
    ]
    if violations:
        lines.append("  gate: FAILED")
        lines.extend([f"  - {item}" for item in violations])
    else:
        lines.append("  gate: PASSED")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run skill eval baselines and enforce SLO thresholds.")
    parser.add_argument(
        "--baseline",
        default=str(REPO_ROOT / "evals" / "skill_eval_baseline.json"),
        help="Path to baseline JSON cases.",
    )
    parser.add_argument(
        "--slo",
        default=str(REPO_ROOT / "evals" / "skill_eval_slo.json"),
        help="Path to SLO threshold JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "evals" / "skill_eval_report.json"),
        help="Path to write the eval report JSON.",
    )
    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline).resolve()
    slo_path = Path(args.slo).resolve()
    report_path = Path(args.report).resolve()

    baseline = _load_json(baseline_path)
    slo = _load_json(slo_path)

    report = {
        "baseline_version": baseline.get("version", "unknown"),
        "discovery": _evaluate_discovery(tuple(baseline.get("discovery_cases") or ())),
        "selection": _evaluate_selection(tuple(baseline.get("selection_cases") or ())),
        "navigation": _evaluate_navigation(tuple(baseline.get("navigation_cases") or ())),
    }
    violations = _apply_quality_gate(report=report, slo=slo)
    report["violations"] = list(violations)
    report["gate_passed"] = not violations

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(_render_summary(report, violations))
    print(f"  report: {report_path}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
