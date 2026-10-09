from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from infinitecontex.capture.git_state import git_status_files, recent_diff_summary
from infinitecontex.capture.repo_scan import scan_behavioral, scan_structural
from infinitecontex.service import InfiniteContextService


def test_scan_skips_links_special_files_and_internal_state(tmp_repo: Path, tmp_path: Path) -> None:
    secret = tmp_path / "outside.py"
    secret.write_text('"""outside sentinel"""\ndef external(): return 1')
    (tmp_repo / "link.py").symlink_to(secret)
    (tmp_repo / "hard.py").hardlink_to(secret)
    (tmp_repo / "outside").symlink_to(tmp_path, target_is_directory=True)
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_repo / "pipe.py")
    struct, fps = scan_structural(tmp_repo, include_patterns=["*"], exclude_patterns=[])
    paths = {fp.path for fp in fps}
    assert paths == {"README.md", "app.py", "pyproject.toml"}
    assert "outside sentinel" not in struct.model_dump_json()
    behavioral = scan_behavioral(tmp_repo, ["link.py", "../outside.py", str(secret)])
    assert behavioral.call_hints == {}


def test_summaries_do_not_read_excluded_or_linked_readme(tmp_repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.md"
    outside.write_text("Private summary sentinel")
    (tmp_repo / "README.md").unlink()
    (tmp_repo / "README.md").symlink_to(outside)
    struct, _ = scan_structural(tmp_repo, include_patterns=["*.py"])
    assert struct.directory_summaries == {}
    assert "sentinel" not in struct.model_dump_json()
    (tmp_repo / "README.md").unlink()
    (tmp_repo / "README.md").write_text("Excluded summary sentinel")
    struct, _ = scan_structural(tmp_repo, exclude_patterns=["README.md"])
    assert "sentinel" not in struct.model_dump_json()


def test_capture_is_deterministic_and_bounded(tmp_repo: Path) -> None:
    (tmp_repo / "000-big.py").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    _, fps = scan_structural(tmp_repo, max_files=2)
    assert [fp.path for fp in fps] == ["README.md", "app.py"]
    _, empty = scan_structural(tmp_repo, include_patterns=[])
    assert empty == []


def test_restore_never_follows_external_paths(tmp_repo: Path, tmp_path: Path) -> None:
    svc = InfiniteContextService(tmp_repo)
    snapshot = svc.snapshot()
    external = tmp_path / "external.py"
    external.write_text("Private restore sentinel")
    (tmp_repo / "app.py").unlink()
    (tmp_repo / "app.py").symlink_to(external)
    result = svc.restore(snapshot.id)
    assert "unsafe or unreadable path: app.py" in result["stale_items"]
    assert "app.py" not in result["still_valid_items"]


@pytest.mark.parametrize("component", [".infctx", ".infctx/metadata", ".infctx/agents"])
def test_rejects_symlinked_state(tmp_repo: Path, tmp_path: Path, component: str) -> None:
    external = tmp_path / "external"
    external.mkdir()
    link = tmp_repo / component
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        InfiniteContextService(tmp_repo).snapshot()
    assert list(external.iterdir()) == []


def test_git_captures_staged_untracked_renames_and_odd_names(tmp_repo: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_repo, check=True, capture_output=True)

    odd_name = 'space → "quote"\nfile.py'
    git("mv", "app.py", odd_name)
    (tmp_repo / "README.md").write_text("staged")
    git("add", "README.md")
    (tmp_repo / "README.md").write_text("also unstaged")
    (tmp_repo / "new.py").write_text("untracked")
    (tmp_repo / ".infctx.lock").touch()
    paths = git_status_files(tmp_repo)
    assert odd_name in paths
    assert {"README.md", "new.py"} <= set(paths)
    assert "app.py" not in paths
    assert ".infctx.lock" not in paths
    summary = recent_diff_summary(tmp_repo)
    assert any("staged + unstaged" in item and "README.md" in item for item in summary)
    assert any("staged" in item and odd_name in item for item in summary)
