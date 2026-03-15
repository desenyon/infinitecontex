"""Repository scanning and lightweight code intelligence."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
from pathlib import Path
from typing import Iterable

from infinitecontex.core.models import BehavioralContext, FileFingerprint, StructuralContext

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
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _matches_pattern(rel, exclude):
            continue
        if not _matches_pattern(rel, include):
            continue
        yield path


def _fingerprint(path: Path, root: Path) -> FileFingerprint:
    data = path.read_bytes()
    stat = path.stat()
    return FileFingerprint(
        path=path.relative_to(root).as_posix(),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha1=hashlib.sha1(data).hexdigest(),
    )


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

    key_files = [f for f in files if Path(f).name in KEY_FILE_NAMES][:40]

    structural = StructuralContext(
        repo_tree_top=sorted({part.split("/")[0] for part in files})[:100],
        key_files=key_files,
        modules=modules,
        entry_points=entry_points,
        config_files=config_files[:80],
        env_files=env_files[:20],
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
