from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from infinitecontex.storage.export_import import import_state


def test_import_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tgz"
    payload = b"x"

    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="../evil.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError):
        import_state(tmp_path, archive)
