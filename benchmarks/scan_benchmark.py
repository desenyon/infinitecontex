from __future__ import annotations

import argparse
import time
from pathlib import Path

from infinitecontex.capture.repo_scan import scan_structural


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()

    start = time.perf_counter()
    structural, fps = scan_structural(args.repo)
    elapsed = time.perf_counter() - start

    print({
        "repo": str(args.repo),
        "elapsed_sec": round(elapsed, 4),
        "files": len(fps),
        "top_dirs": structural.repo_tree_top[:10],
    })


if __name__ == "__main__":
    main()
