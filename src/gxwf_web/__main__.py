"""CLI entry point: uvicorn launcher with --directory."""

import argparse
import json
import os
import sys
from pathlib import Path

import uvicorn

from .app import app, configure, configure_ui


def _build_parser():
    parser = argparse.ArgumentParser(description="Galaxy Workflow Development API")
    parser.add_argument("directory", nargs="?", help="Path to directory containing Galaxy workflows")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument(
        "--output-schema", metavar="FILE", nargs="?", const="-", help="Dump OpenAPI schema and exit (default: stdout)"
    )
    parser.add_argument(
        "--ui-dir", metavar="DIR", help="Path to gxwf-ui dist/ to serve (overrides GXWF_UI_DIST env var and bundled copy)"
    )
    return parser


def main():
    args = _build_parser().parse_args()

    if args.output_schema is not None:
        schema = app.openapi()
        output = json.dumps(schema, indent=2) + "\n"
        if args.output_schema == "-":
            sys.stdout.write(output)
        else:
            with open(args.output_schema, "w") as f:
                f.write(output)
        return

    if not args.directory:
        _build_parser().error("directory is required when not using --output-schema")

    configure(args.directory)

    # UI dir resolution: --ui-dir > GXWF_UI_DIST env var > bundled static/
    ui_dir = args.ui_dir or os.environ.get("GXWF_UI_DIST")
    if ui_dir is None:
        bundled = Path(__file__).parent / "static"
        if bundled.is_dir():
            ui_dir = str(bundled)
    if ui_dir is not None:
        configure_ui(ui_dir)

    uvicorn.run("gxwf_web.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
