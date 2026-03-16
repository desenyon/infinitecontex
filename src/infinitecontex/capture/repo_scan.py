"""Repository scanning and lightweight code intelligence."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Iterable

from infinitecontex.core.models import BehavioralContext, FileFingerprint, FileInsight, StructuralContext

KEY_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
}

FILE_INSIGHT_LIMIT = 20


def _matches_pattern(rel_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/**"):
            prefix = pattern[: -len("/**")].rstrip("/")
            if rel_path == prefix or rel_path.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def _iter_files(
    root: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> Iterable[Path]:
    include = include_patterns or ["**/*", "*"]
    exclude = exclude_patterns or [".git/**", ".infctx/**", ".venv/**", "__pycache__/**", "**/*.pyc"]

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        current_dir = "" if rel_dir == "." else f"{rel_dir}/"

        pruned_dirs = []
        for d in dirnames:
            rel_d = f"{current_dir}{d}"
            if not _matches_pattern(rel_d, exclude):
                pruned_dirs.append(d)
        dirnames[:] = pruned_dirs

        for f in filenames:
            rel = f"{current_dir}{f}"
            if _matches_pattern(rel, exclude):
                continue
            if not _matches_pattern(rel, include):
                continue
            yield Path(dirpath) / f


def _fingerprint(path: Path, root: Path) -> FileFingerprint:
    data = path.read_bytes()
    stat = path.stat()
    return FileFingerprint(
        path=path.relative_to(root).as_posix(),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha1=hashlib.sha1(data).hexdigest(),
    )


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _trim_summary(text: str, max_len: int = 150) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def _python_file_insight(path: Path, root: Path) -> FileInsight:
    rel_path = path.relative_to(root).as_posix()
    src = path.read_text(encoding="utf-8", errors="ignore")

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return FileInsight(path=rel_path, summary="Python module with syntax errors", symbols=[])

    docstring = ast.get_docstring(tree) or ""
    summary = _first_meaningful_line(docstring)
    symbols = [
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ][:8]

    if not summary and symbols:
        summary = f"Defines {', '.join(symbols[:3])}"
    if not summary:
        summary = "Python module"

    return FileInsight(path=rel_path, summary=_trim_summary(summary), symbols=symbols)


def _text_file_insight(path: Path, root: Path) -> FileInsight:
    rel_path = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    summary = _first_meaningful_line(text) or f"Text file: {path.name}"
    return FileInsight(path=rel_path, summary=_trim_summary(summary), symbols=[])


def _build_file_insights(
    root: Path,
    files: list[str],
    key_files: list[str],
    entry_points: list[str],
) -> list[FileInsight]:
    prioritized: list[str] = []
    for rel_path in [*key_files, *entry_points, *files]:
        if rel_path not in prioritized:
            prioritized.append(rel_path)
    insights: list[FileInsight] = []
    for rel_path in prioritized[:FILE_INSIGHT_LIMIT]:
        path = root / rel_path
        if not path.exists() or not path.is_file():
            continue
        if path.suffix == ".py":
            insights.append(_python_file_insight(path, root))
        elif path.suffix in {".md", ".toml", ".json", ".yaml", ".yml", ".ini"} or path.name == "README.md":
            insights.append(_text_file_insight(path, root))
    return insights


def scan_structural(
    root: Path,
    max_files: int = 5_000,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> tuple[StructuralContext, list[FileFingerprint]]:
    files = []
    fingerprints: list[FileFingerprint] = []
    iter_files = _iter_files(root, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    for idx, file_path in enumerate(iter_files):
        if idx >= max_files:
            break
        rel = file_path.relative_to(root).as_posix()
        files.append(rel)
        fingerprints.append(_fingerprint(file_path, root))

    modules: dict[str, list[str]] = {}
    entry_points: list[str] = []
    config_files = [f for f in files if f.endswith((".toml", ".yaml", ".yml", ".ini", ".json"))]
    env_files = [f for f in files if ".env" in f]

    for file_name in files:
        if file_name.endswith(".py"):
            pkg = file_name.replace("/", ".").removesuffix(".py")
            modules.setdefault(pkg.rsplit(".", 1)[0], []).append(pkg)
        if file_name.endswith("__main__.py") or file_name in {"main.py", "app.py", "manage.py"}:
            entry_points.append(file_name)
        if file_name in {"cli.py", "manage.py"} or file_name.endswith("/cli.py"):
            entry_points.append(file_name)

    key_files = [f for f in files if Path(f).name in KEY_FILE_NAMES][:40]

    directory_summaries: dict[str, str] = {}
    for d in sorted(set(Path(f).parent.as_posix() for f in files if f != ".")):
        dpath = root / d
        if not dpath.is_dir():
            continue
        summary = ""
        init_file = dpath / "__init__.py"
        readme_file = dpath / "README.md"
        if readme_file.exists():
            text = readme_file.read_text(encoding="utf-8", errors="ignore").strip()
            lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
            if lines:
                summary = lines[0][:150] + ("..." if len(lines[0]) > 150 else "")
        elif init_file.exists():
            text = init_file.read_text(encoding="utf-8", errors="ignore")
            try:
                tree = ast.parse(text)
                doc = ast.get_docstring(tree)
                if doc:
                    summary = doc.splitlines()[0][:150] + ("..." if len(doc.splitlines()[0]) > 150 else "")
            except Exception:
                pass

        if summary:
            directory_summaries[d] = summary

    structural = StructuralContext(
        repo_tree_top=sorted({part.split("/")[0] for part in files})[:100],
        key_files=key_files,
        modules=modules,
        entry_points=sorted(set(entry_points)),
        config_files=config_files[:80],
        env_files=env_files[:20],
        directory_summaries=directory_summaries,
        file_insights=_build_file_insights(root, files, key_files, entry_points),
    )
    return structural, fingerprints


def scan_behavioral(root: Path, file_paths: list[str]) -> BehavioralContext:
    call_hints: dict[str, list[str]] = {}
    routes_or_commands: list[str] = []
    test_surfaces: list[str] = []
    scripts: dict[str, str] = {}

    for rel in file_paths:
        if rel.endswith(("test.py", "_test.py")) or "tests/" in rel:
            test_surfaces.append(rel)
        if rel == "pyproject.toml":
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if line.strip().startswith("infctx"):
                    scripts["infctx"] = line.strip()

        if rel.endswith(".py"):
            path = root / rel
            src = path.read_text(encoding="utf-8", errors="ignore")
            if "@app." in src or "@router." in src:
                routes_or_commands.append(rel)

            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    calls: list[str] = []
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                            calls.append(sub.func.id)
                    if calls:
                        key = f"{rel}:{node.name}"
                        call_hints[key] = sorted(set(calls))[:20]

    return BehavioralContext(
        call_hints=call_hints,
        scripts=scripts,
        routes_or_commands=sorted(set(routes_or_commands)),
        test_surfaces=sorted(set(test_surfaces)),
    )
