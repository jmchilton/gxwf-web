"""Thin wrappers around galaxy.tool_util.workflow_state operations.

Delegates to the *_single() library entry points — no reimplementation needed.
"""

from pathlib import Path
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
from galaxy.tool_util.workflow_state.export_format2 import (
    ExportSingleResult,
    format_yaml,
)
from galaxy.tool_util.workflow_state.roundtrip import SingleRoundTripReport
from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy
from galaxy.tool_util.workflow_state.to_native_stateful import (
    convert_to_native_stateful,
    format_native_json,
    ToNativeResult,
)
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo
from galaxy.tool_util.workflow_state.workflow_tree import WorkflowInfo

from .models import ConvertResult, ExportResult


def get_tool_info(cache_dir: Optional[str] = None) -> ToolShedGetToolInfo:
    return build_tool_info(cache_dir)


def run_validate(
    info: WorkflowInfo,
    tool_info,
    strict_structure: bool = False,
    strict_encoding: bool = False,
    connections: bool = False,
    mode: str = "pydantic",
    clean_first: bool = False,
    allow: Optional[list] = None,
    deny: Optional[list] = None,
) -> SingleValidationReport:
    policy = StaleKeyPolicy.for_validate(allow or [], deny or [])
    clean_report: Optional[SingleCleanReport] = None
    if clean_first:
        clean_report = clean_single(info.path, tool_info)
    result = validate_single(
        info.path,
        tool_info,
        policy=policy,
        connections=connections,
        clean=clean_first,
        mode=mode,
        strict_structure=strict_structure,
        strict_encoding=strict_encoding,
    )
    result.clean_report = clean_report
    return result


def run_clean(
    info: WorkflowInfo,
    tool_info,
    preserve: Optional[list] = None,
    strip: Optional[list] = None,
    dry_run: bool = False,
) -> SingleCleanReport:
    policy = StaleKeyPolicy.for_clean(preserve or [], strip or [])
    report = clean_single(info.path, tool_info, policy=policy, include_content=True)
    if not dry_run and report.after_content is not None:
        with open(info.path, "w") as f:
            f.write(report.after_content)
    return report


def run_export(
    info: WorkflowInfo,
    tool_info,
    dry_run: bool = False,
) -> ExportResult:
    if info.format == "native":
        result = export_single(info.path, tool_info)
        if result is None:
            raise ValueError("Workflow skipped (legacy encoding)")
        content = format_yaml(result.format2_dict)
        output_path = str(Path(info.path).with_suffix(".gxwf.yml"))
        report = result.report
        source_format = "native"
        target_format = "format2"
    else:
        result = convert_to_native_stateful(info.path, tool_info)
        content = format_native_json(result.native_dict)
        output_path = str(Path(info.path).parent / (Path(Path(info.path).stem).stem + ".ga"))
        report = result
        source_format = "format2"
        target_format = "native"

    if not dry_run:
        with open(output_path, "w") as f:
            f.write(content)

    return ExportResult(
        source_path=info.path,
        output_path=output_path,
        source_format=source_format,
        target_format=target_format,
        report=report,
        dry_run=dry_run,
        content=content if dry_run else None,
    )


def run_convert(
    info: WorkflowInfo,
    tool_info,
    dry_run: bool = False,
) -> ConvertResult:
    if info.format == "native":
        result = export_single(info.path, tool_info)
        if result is None:
            raise ValueError("Workflow skipped (legacy encoding)")
        content = format_yaml(result.format2_dict)
        output_path = str(Path(info.path).with_suffix(".gxwf.yml"))
        report = result.report
        source_format = "native"
        target_format = "format2"
    else:
        result = convert_to_native_stateful(info.path, tool_info)
        content = format_native_json(result.native_dict)
        output_path = str(Path(info.path).parent / (Path(Path(info.path).stem).stem + ".ga"))
        report = result
        source_format = "format2"
        target_format = "native"

    removed_path = info.path

    if not dry_run:
        with open(output_path, "w") as f:
            f.write(content)
        Path(removed_path).unlink()

    return ConvertResult(
        source_path=info.path,
        output_path=output_path,
        removed_path=removed_path,
        source_format=source_format,
        target_format=target_format,
        report=report,
        dry_run=dry_run,
        content=content if dry_run else None,
    )


def run_roundtrip(
    info: WorkflowInfo,
    tool_info,
    strict_structure: bool = False,
    strict_encoding: bool = False,
    strict_state: bool = False,
    include_content: bool = False,
) -> SingleRoundTripReport:
    return roundtrip_single(
        info.path,
        tool_info,
        strict_structure=strict_structure,
        strict_encoding=strict_encoding,
        strict_state=strict_state,
        include_content=include_content,
    )


def run_lint(
    info: WorkflowInfo,
    tool_info,
    strict_structure: bool = False,
    strict_encoding: bool = False,
    allow: Optional[list] = None,
    deny: Optional[list] = None,
) -> SingleLintReport:
    policy = StaleKeyPolicy.for_validate(allow or [], deny or [])
    return lint_single(
        info.path,
        tool_info,
        policy=policy,
        strict_structure=strict_structure,
        strict_encoding=strict_encoding,
    )
