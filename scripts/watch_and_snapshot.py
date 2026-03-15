from __future__ import annotations

import argparse
from pathlib import Path

from watchfiles import watch

from infinitecontex.service import InfiniteContextService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--goal", default="")
    parser.add_argument("--debounce", type=int, default=1200)
    args = parser.parse_args()

    svc = InfiniteContextService(args.repo.resolve())
    svc.init()

    for _ in watch(args.repo, debounce=args.debounce):
        snap = svc.snapshot(goal=args.goal)
        print(f"snapshot: {snap.id}")


if __name__ == "__main__":
    main()
