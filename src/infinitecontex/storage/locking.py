"""Reentrant, process-wide advisory locking for cooperating local writers."""

from __future__ import annotations

import importlib
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from infinitecontex.storage.paths import checked_path

_mutex = threading.RLock()
_local = threading.local()


@contextmanager
def project_lock(root: Path) -> Iterator[None]:
    # One in-process mutex also protects the per-thread recursion bookkeeping.
    with _mutex:
        key = str(root.resolve())
        held: set[str] = getattr(_local, "held", set())
        if key in held:
            yield
            return
        root.mkdir(parents=True, exist_ok=True)
        path = checked_path(root, root.resolve() / ".infctx.lock")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            if os.name == "nt":
                msvcrt = importlib.import_module("msvcrt")
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"0")
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX)
            held.add(key)
            _local.held = held
            # Recover the old tree if a process died between the two import renames.
            backup = checked_path(root, root.resolve() / ".infctx-import-backup")
            state = checked_path(root, root.resolve() / ".infctx")
            if backup.exists() and not state.exists():
                backup.rename(state)
            yield
        finally:
            held.discard(key)
            os.close(fd)
