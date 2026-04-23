from __future__ import annotations

from pathlib import Path

from infinitecontex.capture.repo_scan import scan_structural


def test_scan_respects_include_exclude_patterns(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "app.py").write_text("print('root')\n", encoding="utf-8")
    (root / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "src" / "ignore.pyc").write_text("x", encoding="utf-8")
    (root / "README.md").write_text("r", encoding="utf-8")
    (root / ".pytest_cache").mkdir()
    (root / ".pytest_cache" / "state").write_text("x", encoding="utf-8")

    structural, fingerprints = scan_structural(
        root,
        include_patterns=["**/*.py", "README.md"],
        exclude_patterns=["**/*.pyc", ".pytest_cache/**"],
    )

    paths = {fp.path for fp in fingerprints}
    assert "app.py" in paths
    assert "src/a.py" in paths
    assert "README.md" in paths
    assert "src/ignore.pyc" not in paths
    assert ".pytest_cache/state" not in paths
    assert "README.md" in structural.key_files
