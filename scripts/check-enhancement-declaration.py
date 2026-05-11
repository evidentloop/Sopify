#!/usr/bin/env python3
"""Validate host enhancement declarations against governance expectations.

Checks that each registered host's declared_enhancements align with the
policy expectations derived from its support_tier and the consumption matrix
(see blueprint/design.md P4c-2 governance expectation table).

Exit codes:
  0 — always (advisory check, never blocks)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from installer.hosts import iter_declared_hosts
from installer.models import EnhancementGroup, SupportTier

ALL_GROUPS = frozenset(EnhancementGroup)

TIER_EXPECTATIONS: dict[SupportTier, frozenset[EnhancementGroup]] = {
    SupportTier.DEEP_VERIFIED: ALL_GROUPS,
    SupportTier.BASELINE_SUPPORTED: frozenset({EnhancementGroup.CONTINUATION}),
    SupportTier.EXPERIMENTAL: frozenset(),
    SupportTier.DOCUMENTED_ONLY: frozenset(),
}


def check_host(host_id: str, tier: SupportTier, declared: frozenset[EnhancementGroup]) -> list[str]:
    """Return advisory warnings for one host."""
    warnings: list[str] = []
    expected = TIER_EXPECTATIONS.get(tier, frozenset())

    missing = expected - declared
    if missing:
        labels = ", ".join(sorted(g.value for g in missing))
        warnings.append(f"[{host_id}] tier={tier.value} expects [{labels}] but not declared")

    if tier == SupportTier.DEEP_VERIFIED and declared != ALL_GROUPS:
        labels = ", ".join(sorted(g.value for g in ALL_GROUPS - declared))
        warnings.append(f"[{host_id}] deep_verified should declare all groups; missing: [{labels}]")

    return warnings


def main() -> int:
    all_warnings: list[str] = []
    checked = 0

    for cap in iter_declared_hosts():
        declared = frozenset(cap.declared_enhancements)
        warnings = check_host(cap.host_id, cap.support_tier, declared)
        all_warnings.extend(warnings)
        checked += 1

        status = "PASS" if not warnings else "WARN"
        groups_str = ", ".join(g.value for g in cap.declared_enhancements) or "(none)"
        print(f"  {status}  {cap.host_id}  tier={cap.support_tier.value}  enhancements=[{groups_str}]")

    print()
    if all_warnings:
        print(f"Advisory warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  ⚠  {w}")
        print()
        print("(advisory only — does not block)")
        return 0

    print(f"All {checked} host(s) pass enhancement declaration check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
