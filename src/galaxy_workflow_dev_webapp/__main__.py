"""CLI entry point: uvicorn launcher with --directory."""

import argparse
import json
import sys

import uvicorn

from .app import app, configure


def _build_parser():
    parser = argparse.ArgumentParser(description="Galaxy Workflow Development API")
    parser.add_argument("directory", nargs="?", help="Path to directory containing Galaxy workflows")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument(
        "--output-schema", metavar="FILE", nargs="?", const="-", help="Dump OpenAPI schema and exit (default: stdout)"
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
    uvicorn.run("galaxy_workflow_dev_webapp.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
