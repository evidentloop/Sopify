"""Copilot host adapter."""

from __future__ import annotations

from installer.models import EntryMode, FeatureId, HostCapability, SupportTier

from .base import INSTRUCTION_SURFACE_SINGLE_FILE, HostAdapter, HostRegistration

COPILOT_ADAPTER = HostAdapter(
    host_name="copilot",
    destination_dirname=".github",
    header_filename="copilot-instructions.md",
    config_dir=None,
    instruction_surface=INSTRUCTION_SURFACE_SINGLE_FILE,
    instruction_file_relpath=None,
    default_language="en-US",
)

COPILOT_CAPABILITY = HostCapability(
    host_id="copilot",
    support_tier=SupportTier.BASELINE_SUPPORTED,
    install_enabled=True,
    declared_features=(
        FeatureId.PROMPT_INSTALL,
    ),
    verified_features=(
        FeatureId.PROMPT_INSTALL,
    ),
    declared_enhancements=(),
    entry_modes=(EntryMode.PROMPT_ONLY,),
    doctor_checks=(
        "host_prompt_present",
    ),
    smoke_targets=(),
)

COPILOT_HOST = HostRegistration(adapter=COPILOT_ADAPTER, capability=COPILOT_CAPABILITY)
