"""Fast local serialization helpers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, cast

import orjson


def dump_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    atomic_write(path, orjson.dumps(payload, option=orjson.OPT_INDENT_2))


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], orjson.loads(path.read_bytes()))


def atomic_write(path: Path, data: bytes) -> None:
    """Replace a complete file; failed writes leave the previous version intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to write a symlink: {path}")
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_text(path: Path, text: str) -> None:
    atomic_write(path, text.encode("utf-8"))
