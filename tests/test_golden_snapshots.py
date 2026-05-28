"""T6 golden snapshot — verify install products haven't drifted.

Compares sha256 hashes of all host install products (rendered from skills/)
against the baseline recorded in tests/golden-snapshots.json.

Products covered:
  - codex:{locale}:header         — path\\0rendered_header (AGENTS.md)
  - claude:{locale}:header        — path\\0rendered_header (CLAUDE.md)
  - copilot:{locale}:managed_block_payload — render_single_file() output
  - skills:{locale}:tree          — sorted path\\0content of skills/sopify/**

When a snapshot fails, the test prints the expected vs actual hash and the
snapshot key. Update tests/golden-snapshots.json manually after confirming
the change is intentional.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from installer.hosts.base import (
    HEADER_TEMPLATE_NAME,
    HostAdapter,
    render_single_file,
)
from installer.hosts.claude import CLAUDE_ADAPTER
from installer.hosts.codex import CODEX_ADAPTER
from installer.hosts.copilot import COPILOT_ADAPTER
from installer.models import language_to_source_dir

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GOLDEN_PATH = Path(__file__).resolve().parent / "golden-snapshots.json"
_IGNORE_NAMES = {".DS_Store", "Thumbs.db", "__pycache__"}


def _load_golden() -> dict:
    with open(_GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)["snapshots"]


def _render_header(adapter: HostAdapter, lang_dir: str) -> str:
    source_root = adapter.source_root(_REPO_ROOT, lang_dir)
    template = source_root / HEADER_TEMPLATE_NAME
    content = template.read_text(encoding="utf-8")
    if adapter.config_dir is not None:
        content = content.replace("{{config_dir}}", adapter.config_dir)
    else:
        content = content.replace("{{config_dir}}", "")
    return content


def _header_hash(adapter: HostAdapter, lang_dir: str) -> str:
    rendered = _render_header(adapter, lang_dir)
    canonical = f"{adapter.header_filename}\x00{rendered}".encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _tree_hash(lang_dir: str) -> str:
    source_dir = language_to_source_dir(lang_dir)
    skills_root = _REPO_ROOT / "skills" / source_dir / "skills" / "sopify"
    parts: list[bytes] = []
    for f in sorted(skills_root.rglob("*")):
        if f.is_file() and f.name not in _IGNORE_NAMES:
            rel = f.relative_to(skills_root).as_posix()
            parts.append(rel.encode("utf-8") + b"\x00" + f.read_bytes())
    return hashlib.sha256(b"\n".join(parts)).hexdigest()


def _copilot_payload_hash(lang_dir: str) -> str:
    source_root = COPILOT_ADAPTER.source_root(_REPO_ROOT, lang_dir)
    header_source = source_root / HEADER_TEMPLATE_NAME
    skills_source = source_root / "skills" / "sopify"
    rendered = render_single_file(header_source, skills_source, COPILOT_ADAPTER)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _assert_hash(key: str, actual: str, golden: dict) -> None:
    expected = golden.get(key)
    assert expected is not None, f"Missing golden entry: {key}"
    assert actual == expected, (
        f"Golden snapshot mismatch for {key}\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        f"Update tests/golden-snapshots.json if this change is intentional."
    )


# -- Header snapshots (Codex / Claude) --

@pytest.mark.parametrize(
    "adapter,lang_dir,locale",
    [
        (CODEX_ADAPTER, "CN", "zh-CN"),
        (CODEX_ADAPTER, "EN", "en-US"),
        (CLAUDE_ADAPTER, "CN", "zh-CN"),
        (CLAUDE_ADAPTER, "EN", "en-US"),
    ],
    ids=["codex:zh-CN", "codex:en-US", "claude:zh-CN", "claude:en-US"],
)
def test_header_snapshot(adapter: HostAdapter, lang_dir: str, locale: str) -> None:
    golden = _load_golden()
    key = f"{adapter.host_name}:{locale}:header"
    actual = _header_hash(adapter, lang_dir)
    _assert_hash(key, actual, golden)


# -- Copilot managed block payload snapshots --

@pytest.mark.parametrize(
    "lang_dir,locale",
    [("CN", "zh-CN"), ("EN", "en-US")],
    ids=["copilot:zh-CN", "copilot:en-US"],
)
def test_copilot_payload_snapshot(lang_dir: str, locale: str) -> None:
    golden = _load_golden()
    key = f"copilot:{locale}:managed_block_payload"
    actual = _copilot_payload_hash(lang_dir)
    _assert_hash(key, actual, golden)


# -- Skill tree snapshots --

@pytest.mark.parametrize(
    "lang_dir,locale",
    [("CN", "zh-CN"), ("EN", "en-US")],
    ids=["skills:zh-CN", "skills:en-US"],
)
def test_skill_tree_snapshot(lang_dir: str, locale: str) -> None:
    golden = _load_golden()
    key = f"skills:{locale}:tree"
    actual = _tree_hash(lang_dir)
    _assert_hash(key, actual, golden)


# -- Template structure assertions --

_ZH_TEMPLATE_MARKERS: list[tuple[str, list[str]]] = [
    ("develop/assets/output-success.md", ["| 任务 |", "| 验证来源 |", "Changes:", "Next:"]),
    ("develop/assets/output-partial.md", ["| 任务 |", "| 阻塞原因 |", "| 验证来源 |", "Changes:", "Next:"]),
    ("develop/assets/output-quick-fix.md", ["| 验证来源 |", "Changes:", "Next:"]),
    ("analyze/assets/success-output.md", ["假设与前提:", "已识别信息缺口:", "Changes:", "Next:"]),
    ("design/assets/output-summary.md", ["方案质量:", "落地就绪:", "Changes:", "Next:"]),
]

_EN_TEMPLATE_MARKERS: list[tuple[str, list[str]]] = [
    ("develop/assets/output-success.md", ["| Task |", "| Source |", "Changes:", "Next:"]),
    ("develop/assets/output-partial.md", ["| Task |", "| Block reason |", "| Source |", "Changes:", "Next:"]),
    ("develop/assets/output-quick-fix.md", ["| Source |", "Changes:", "Next:"]),
    ("analyze/assets/success-output.md", ["Assumptions:", "Identified gaps:", "Changes:", "Next:"]),
    ("design/assets/output-summary.md", ["Solution quality:", "Implementation readiness:", "Changes:", "Next:"]),
]


def _template_cases() -> list[tuple[str, str, list[str]]]:
    cases: list[tuple[str, str, list[str]]] = []
    for rel, markers in _ZH_TEMPLATE_MARKERS:
        cases.append(("CN", rel, markers))
    for rel, markers in _EN_TEMPLATE_MARKERS:
        cases.append(("EN", rel, markers))
    return cases


@pytest.mark.parametrize(
    "lang_dir,template_rel,required_markers",
    _template_cases(),
    ids=[f"{lang}:{rel}" for lang, rel, _ in _template_cases()],
)
def test_template_required_sections(
    lang_dir: str, template_rel: str, required_markers: list[str]
) -> None:
    """Verify that output templates contain their required structural markers."""
    source_dir = language_to_source_dir(lang_dir)
    template_path = _REPO_ROOT / "skills" / source_dir / "skills" / "sopify" / template_rel
    assert template_path.is_file(), f"Template not found: {template_path}"
    content = template_path.read_text(encoding="utf-8")
    for marker in required_markers:
        assert marker in content, (
            f"Required marker missing in {template_rel} ({lang_dir}): {marker!r}"
        )


# -- Output contract inline assertions (all 3 hosts) --

def _render_full(adapter: HostAdapter, lang_dir: str) -> str:
    source_root = adapter.source_root(_REPO_ROOT, lang_dir)
    header_source = source_root / HEADER_TEMPLATE_NAME
    skills_source = source_root / "skills" / "sopify"
    return render_single_file(header_source, skills_source, adapter)


_OUTPUT_CONTRACT_ZH_MARKERS = ["输出契约", "必需 section", "Conditional Enhancement & Format Selection"]
_OUTPUT_CONTRACT_EN_MARKERS = ["Output Contract", "Required Sections", "Conditional Enhancement & Format Selection"]


@pytest.mark.parametrize(
    "adapter,lang_dir,markers",
    [
        (CODEX_ADAPTER, "CN", _OUTPUT_CONTRACT_ZH_MARKERS),
        (CODEX_ADAPTER, "EN", _OUTPUT_CONTRACT_EN_MARKERS),
        (CLAUDE_ADAPTER, "CN", _OUTPUT_CONTRACT_ZH_MARKERS),
        (CLAUDE_ADAPTER, "EN", _OUTPUT_CONTRACT_EN_MARKERS),
        (COPILOT_ADAPTER, "CN", _OUTPUT_CONTRACT_ZH_MARKERS),
        (COPILOT_ADAPTER, "EN", _OUTPUT_CONTRACT_EN_MARKERS),
    ],
    ids=[
        "codex:zh-CN:contract", "codex:en-US:contract",
        "claude:zh-CN:contract", "claude:en-US:contract",
        "copilot:zh-CN:contract", "copilot:en-US:contract",
    ],
)
def test_output_contract_inlined(
    adapter: HostAdapter, lang_dir: str, markers: list[str]
) -> None:
    """Verify that output-contract.md is inlined into the rendered prompt for all hosts."""
    rendered = _render_full(adapter, lang_dir)
    for marker in markers:
        assert marker in rendered, (
            f"Output contract marker missing in {adapter.host_name} ({lang_dir}): {marker!r}\n"
            f"Ensure references/output-contract.md exists and render pipeline inlines it."
        )
