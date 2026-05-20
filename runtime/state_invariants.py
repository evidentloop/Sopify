"""Domain-level validators for runtime checkpoint state writes.

Canonical definitions have been extracted to canonical_writer.invariants.
This module re-exports them for backward compatibility.
"""

from canonical_writer.invariants import (  # noqa: F401
    ALLOWED_PHASES_BY_STATE_KIND,
    HOST_FACING_TRUTH_WRITE_KINDS,
    InvariantViolationError,
    is_supported_phase,
    stamp_handoff_resolution_id,
    stamp_run_resolution_id,
    validate_host_facing_truth_write_kind,
    validate_paired_host_truth_write,
    validate_phase,
    validate_resolution_id,
)
