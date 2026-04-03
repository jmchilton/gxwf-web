"""CLI entry point: uvicorn launcher with --directory."""

import argparse

import uvicorn

from .app import configure


def _build_parser():
    parser = argparse.ArgumentParser(description="Galaxy Workflow Development API")
    parser.add_argument("directory", help="Path to directory containing Galaxy workflows")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    return parser


def main():
    args = _build_parser().parse_args()

    configure(args.directory)
    uvicorn.run("galaxy_workflow_dev_webapp.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
