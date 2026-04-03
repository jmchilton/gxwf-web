"""Thin wrappers around galaxy.tool_util.workflow_state operations.

Each function takes a workflow path + options, returns a Pydantic report model.
These are the bridge between the FastAPI routes and the library.
"""

import logging
from typing import (
    List,
    Optional,
)

from gxformat2.normalized import ensure_native

from galaxy.tool_util.workflow_state._report_models import (
    SingleCleanReport,
    SingleLintReport,
    SingleValidationReport,
    ValidationStepResult,
)
from galaxy.tool_util.workflow_state._types import GetToolInfo
from galaxy.tool_util.workflow_state.cache import build_tool_info
from galaxy.tool_util.workflow_state.clean import clean_stale_state
from galaxy.tool_util.workflow_state.export_format2 import export_workflow_to_format2
from galaxy.tool_util.workflow_state.lint_stateful import (
    run_structural_lint,
)
from galaxy.tool_util.workflow_state.roundtrip import (
    roundtrip_validate,
    RoundTripValidationResult,
)
from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo
from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
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
    wf_dict = load_workflow(info.path)
    policy = StaleKeyPolicy.for_validate(allow or [], deny or [])

    if mode == "json-schema":
        from galaxy.tool_util.workflow_state.validation_json_schema import (
            validate_native_workflow_json_schema,
            validate_workflow_json_schema,
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

    results, precheck, connection_report = validate_workflow_cli(
        wf_dict,
        tool_info,
        policy=policy,
        connections=connections,
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
    wf_dict = load_workflow(info.path)
    policy = StaleKeyPolicy.for_clean(preserve or [], strip or [])
    normalized = ensure_native(wf_dict)
    clean_result = clean_stale_state(normalized, wf_dict, tool_info, policy=policy)
    return SingleCleanReport(
        workflow=info.relative_path,
        results=list(clean_result.step_results),
    )


def run_export_format2(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
) -> dict:
    wf_dict = load_workflow(info.path)
    normalized = ensure_native(wf_dict)
    result = export_workflow_to_format2(normalized, tool_info)
    return result.format2.to_dict()


def run_roundtrip(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
) -> RoundTripValidationResult:
    wf_dict = load_workflow(info.path)
    return roundtrip_validate(wf_dict, tool_info, workflow_path=info.path)


def run_lint(
    info: WorkflowInfo,
    tool_info: GetToolInfo,
    strict: bool = False,
    allow: Optional[List[str]] = None,
    deny: Optional[List[str]] = None,
) -> SingleLintReport:
    from gxformat2.yaml import ordered_load_path

    workflow_dict = ordered_load_path(info.path)
    lint_context = run_structural_lint(workflow_dict)
    policy = StaleKeyPolicy.for_validate(allow or [], deny or [])
    results, precheck, conn_report = validate_workflow_cli(
        workflow_dict,
        tool_info,
        policy=policy,
    )
    return SingleLintReport(
        workflow=info.relative_path,
        lint_errors=len(lint_context.error_messages),
        lint_warnings=len(lint_context.warn_messages),
        results=results,
    )
