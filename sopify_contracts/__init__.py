"""Shared contract types for the Sopify runtime ecosystem.

Migrated from runtime/_models/ as a top-level shared package.
All runtime and canonical_writer modules import types from here.
"""

from .artifacts import KbArtifact, PlanArtifact
from .core import ExecutionGate, ExecutionSummary, RouteDecision, RunState, RuntimeConfig, SkillMeta
from .decision import (
    ClarificationState,
    DecisionCheckpoint,
    DecisionCondition,
    DecisionField,
    DecisionOption,
    DecisionRecommendation,
    DecisionSelection,
    DecisionState,
    DecisionSubmission,
    DecisionValidation,
)
from .handoff import RecoveredContext, RuntimeHandoff, RuntimeResult, SkillActivation
from .proposal import PlanProposalState

__all__ = [
    "ClarificationState",
    "DecisionCheckpoint",
    "DecisionCondition",
    "DecisionField",
    "DecisionOption",
    "DecisionRecommendation",
    "DecisionSelection",
    "DecisionState",
    "DecisionSubmission",
    "DecisionValidation",
    "ExecutionGate",
    "ExecutionSummary",
    "KbArtifact",
    "PlanArtifact",
    "PlanProposalState",
    "RecoveredContext",
    "RouteDecision",
    "RunState",
    "RuntimeConfig",
    "RuntimeHandoff",
    "RuntimeResult",
    "SkillActivation",
    "SkillMeta",
]
