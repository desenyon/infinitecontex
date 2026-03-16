from infinitecontex.capture.repo_scan import scan_behavioral, scan_structural


def test_scan_structural_directory_summaries(tmp_path):
    # Setup directories
    d1 = tmp_path / "mod_a"
    d1.mkdir()
    (d1 / "__init__.py").write_text('"""Module A does things\nAnd more things."""')
    # Valid file so directory is included
    (d1 / "file.py").write_text("")

    d2 = tmp_path / "mod_b"
    d2.mkdir()
    (d2 / "README.md").write_text("# Title\nMod B README summary.\nMore lines.")
    (d2 / "file.py").write_text("")

    # Broken AST case
    d3 = tmp_path / "mod_c"
    d3.mkdir()
    (d3 / "__init__.py").write_text("invalid syntax [[[")
    (d3 / "file.py").write_text("")

    # Exceed length case
    d4 = tmp_path / "mod_d"
    d4.mkdir()
    long_desc = "x" * 200
    (d4 / "README.md").write_text(long_desc)
    (d4 / "file.py").write_text("")

    # Not a dir case (simulate by adding a file and relying on the parent check)
    f_root = tmp_path / "root_file.py"
    f_root.write_text("")

    # Main entry point test
    f_main = tmp_path / "__main__.py"
    f_main.write_text("")

    struct, fingerprints = scan_structural(tmp_path, max_files=10)

    assert "mod_a" in struct.directory_summaries
    assert struct.directory_summaries["mod_a"] == "Module A does things"

    assert "mod_b" in struct.directory_summaries
    assert struct.directory_summaries["mod_b"] == "Mod B README summary."

    assert "mod_c" not in struct.directory_summaries

    assert "mod_d" in struct.directory_summaries
    assert struct.directory_summaries["mod_d"].endswith("...")
    assert len(struct.directory_summaries["mod_d"]) == 153

    assert "__main__.py" in struct.entry_points


def test_scan_structural_max_files(tmp_path):
    for i in range(5):
        (tmp_path / f"f_{i}.py").write_text("")

    # Should only return 2 files
    struct, fingerprints = scan_structural(tmp_path, max_files=2)
    assert len(fingerprints) == 2


def test_scan_structural_collects_file_insights(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\nUseful project summary.\n", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        '"""CLI entrypoint."""\n\n\ndef run_app():\n    return "ok"\n',
        encoding="utf-8",
    )

    struct, _ = scan_structural(tmp_path, max_files=10)

    assert struct.file_insights
    assert any(item.path == "app.py" for item in struct.file_insights)
    app_insight = next(item for item in struct.file_insights if item.path == "app.py")
    assert "CLI entrypoint" in app_insight.summary
    assert "run_app" in app_insight.symbols


def test_scan_structural_include_miss(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("")

    # Line 59 coverage: Exclude a specific file pattern
    f2 = tmp_path / "secret.py"
    f2.write_text("")

    # Line 31 coverage: directory exclude
    d = tmp_path / "hidden_dir"
    d.mkdir()
    (d / "file.py").write_text("")

    struct, fingerprints = scan_structural(
        tmp_path, include_patterns=["**/*.py"], exclude_patterns=[".git/**", "secret.py", "hidden_dir/**"]
    )
    names = [fp.path for fp in fingerprints]
    assert "test.txt" not in names
    assert "secret.py" not in names
    assert "hidden_dir/file.py" not in names


def test_scan_structural_deleted_dir(tmp_path):
    d = tmp_path / "temp_mod"
    d.mkdir()
    (d / "file.py").write_text("")

    from unittest.mock import patch

    # Mock is_dir to return False specifically for this test to hit line 110
    with patch("pathlib.Path.is_dir", return_value=False):
        struct, fingerprints = scan_structural(tmp_path)
        assert "temp_mod" not in struct.directory_summaries


def test_scan_behavioral(tmp_path):
    (tmp_path / "app_test.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "unit.py").write_text("")

    (tmp_path / "pyproject.toml").write_text('infctx = "uv run infctx"')

    src = """
@app.route("/")
def home():
    print("hi")
    load_data()
"""
    (tmp_path / "routes.py").write_text(src)
    (tmp_path / "broken.py").write_text("def broken[:")

    files = ["app_test.py", "tests/unit.py", "pyproject.toml", "routes.py", "broken.py"]

    beh = scan_behavioral(tmp_path, files)

    assert "app_test.py" in beh.test_surfaces
    assert "tests/unit.py" in beh.test_surfaces
    assert "infctx" in beh.scripts
    assert "routes.py" in beh.routes_or_commands
    assert "routes.py:home" in beh.call_hints
    assert "load_data" in beh.call_hints["routes.py:home"]
