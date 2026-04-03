"""Thin wrappers around galaxy.tool_util.workflow_state operations.

Delegates to the *_single() library entry points — no reimplementation needed.
"""

from typing import Optional

from galaxy.tool_util.workflow_state import (
    clean_single,
    export_single,
    lint_single,
    roundtrip_single,
    validate_single,
)
from galaxy.tool_util.workflow_state._report_models import (
    SingleCleanReport,
    SingleLintReport,
    SingleValidationReport,
)
from galaxy.tool_util.workflow_state.cache import build_tool_info
from galaxy.tool_util.workflow_state.export_format2 import ExportSingleResult
from galaxy.tool_util.workflow_state.roundtrip import SingleRoundTripReport
from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo
from galaxy.tool_util.workflow_state.workflow_tree import WorkflowInfo


def get_tool_info(cache_dir: Optional[str] = None) -> ToolShedGetToolInfo:
    return build_tool_info(cache_dir)


def run_validate(info: WorkflowInfo, tool_info, **kwargs) -> SingleValidationReport:
    policy = StaleKeyPolicy.for_validate(kwargs.pop("allow", []), kwargs.pop("deny", []))
    return validate_single(info.path, tool_info, policy=policy, **kwargs)


def run_clean(info: WorkflowInfo, tool_info, **kwargs) -> SingleCleanReport:
    policy = StaleKeyPolicy.for_clean(kwargs.pop("preserve", []), kwargs.pop("strip", []))
    return clean_single(info.path, tool_info, policy=policy)


def run_export_format2(info: WorkflowInfo, tool_info) -> Optional[ExportSingleResult]:
    return export_single(info.path, tool_info)


def run_roundtrip(info: WorkflowInfo, tool_info) -> SingleRoundTripReport:
    return roundtrip_single(info.path, tool_info)


def run_lint(info: WorkflowInfo, tool_info, **kwargs) -> SingleLintReport:
    policy = StaleKeyPolicy.for_validate(kwargs.pop("allow", []), kwargs.pop("deny", []))
    return lint_single(info.path, tool_info, policy=policy, **kwargs)
