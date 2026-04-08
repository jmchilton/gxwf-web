#!/usr/bin/env python3
"""Copy a built gxwf-ui dist/ into src/gxwf_web/static/.

Usage:
    python scripts/copy_ui.py <path-to-gxwf-ui-dist>

Example (from the galaxy-tool-util monorepo worktree):
    python scripts/copy_ui.py ../worktrees/galaxy-tool-util/branch/styling/packages/gxwf-ui/dist
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent
DEST = HERE / "src" / "gxwf_web" / "static"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    src = Path(sys.argv[1]).resolve()
    if not (src / "index.html").is_file():
        print(f"Error: {src} does not look like a Vite dist/ (no index.html)", file=sys.stderr)
        sys.exit(1)
    if not (src / "assets").is_dir():
        print(f"Error: {src} missing assets/ subdirectory", file=sys.stderr)
        sys.exit(1)

    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(src, DEST)
    print(f"Copied {src} -> {DEST}")


if __name__ == "__main__":
    main()
