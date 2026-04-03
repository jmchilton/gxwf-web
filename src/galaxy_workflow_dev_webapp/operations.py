"""Thin wrappers around galaxy.tool_util.workflow_state operations.

Each function takes a workflow path + options, returns a Pydantic report model.
These are the bridge between the FastAPI routes and the library.
"""

import json
import logging
from typing import (
    List,
    Optional,
)

from galaxy.tool_util.workflow_state._report_models import (
    SingleCleanReport,
    SingleLintReport,
    SingleValidationReport,
    ValidationStepResult,
)
from galaxy.tool_util.workflow_state._types import GetToolInfo
from galaxy.tool_util.workflow_state.cache import build_tool_info
from galaxy.tool_util.workflow_state.clean import (
    clean_stale_state,
)
from galaxy.tool_util.workflow_state.export_format2 import (
    export_one_workflow,
)
from galaxy.tool_util.workflow_state.roundtrip import (
    roundtrip_one_workflow,
    RoundTripResult,
)
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo
from galaxy.tool_util.workflow_state.workflow_tools import load_workflow
from galaxy.tool_util.workflow_state.workflow_tree import WorkflowInfo

log = logging.getLogger(__name__)


def get_tool_info(cache_dir: Optional[str] = None) -> ToolShedGetToolInfo:
    return build_tool_info(cache_dir)


def run_validate(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
    strict: bool = False,
    connections: bool = False,
    mode: str = "pydantic",
    allow: Optional[List[str]] = None,
    deny: Optional[List[str]] = None,
) -> SingleValidationReport:
    from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
    from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy

    wf_dict = load_workflow(info.path)
    policy = StaleKeyPolicy.from_lists(allow=allow or [], deny=deny or [])

    if mode == "json-schema":
        from galaxy.tool_util.workflow_state.validation_json_schema import (
            validate_workflow_json_schema,
            validate_native_workflow_json_schema,
        )
        if info.format == "format2":
            results = validate_workflow_json_schema(wf_dict, tool_info)
        else:
            results = validate_native_workflow_json_schema(wf_dict, tool_info)
        step_results = [
            ValidationStepResult(
                step=r.get("step", "?"),
                tool_id=r.get("tool_id"),
                status="ok" if not r.get("errors") else "fail",
                errors=r.get("errors", []),
            )
            for r in results
        ]
        return SingleValidationReport(
            workflow=info.relative_path,
            results=step_results,
        )

    results, connection_report = validate_workflow_cli(
        wf_dict,
        info,
        tool_info,
        policy=policy,
        run_connections=connections,
    )
    return SingleValidationReport(
        workflow=info.relative_path,
        results=results,
        connection_report=connection_report,
    )


def run_clean(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
    preserve: Optional[List[str]] = None,
    strip: Optional[List[str]] = None,
) -> SingleCleanReport:
    from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy

    wf_dict = load_workflow(info.path)
    policy = StaleKeyPolicy.from_lists(allow=preserve or [], deny=strip or [])
    step_results = clean_stale_state(wf_dict, tool_info, policy=policy)
    return SingleCleanReport(
        workflow=info.relative_path,
        results=step_results,
    )


def run_export_format2(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
) -> dict:
    result = export_one_workflow(info, tool_info)
    return result


def run_roundtrip(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
) -> RoundTripResult:
    return roundtrip_one_workflow(info, tool_info)


def run_lint(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
    strict: bool = False,
    allow: Optional[List[str]] = None,
    deny: Optional[List[str]] = None,
) -> SingleLintReport:
    from galaxy.tool_util.workflow_state.lint_stateful import lint_one_workflow

    result = lint_one_workflow(info, tool_info, allow=allow or [], deny=deny or [])
    return result
