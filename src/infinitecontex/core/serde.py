"""Fast local serialization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import orjson


def dump_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], orjson.loads(path.read_bytes()))
