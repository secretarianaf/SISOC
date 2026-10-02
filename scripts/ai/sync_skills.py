"""Sincroniza las skills del repo de `.agents/skills/` a `.claude/skills/`.

La fuente vive en `.agents/skills/` (la lee Codex). Claude Code lee
`.claude/skills/`, que es una copia generada: no se edita a mano. No se usan
symlinks porque se rompen en Windows con `core.symlinks=false`.

Uso:
    python scripts/ai/sync_skills.py          # copia, actualiza y borra sobrantes
    python scripts/ai/sync_skills.py --check  # falla (exit 1) si la copia difiere

Solo stdlib. Ver docs/ia/SKILLS.md.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / ".agents" / "skills"
TARGET_DIR = REPO_ROOT / ".claude" / "skills"
IGNORED_NAMES = {"__pycache__", ".DS_Store"}


def _files(base: Path) -> dict[str, Path]:
    """Archivos bajo `base`, por ruta relativa POSIX."""

    if not base.is_dir():
        return {}
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file() and not IGNORED_NAMES.intersection(path.parts)
    }


def _same_content(left: Path, right: Path) -> bool:
    # Se comparan sin distinguir CRLF/LF: con core.autocrlf el checkout de
    # Windows puede cambiar los finales de línea de uno solo de los dos lados.
    return left.read_bytes().replace(b"\r\n", b"\n") == right.read_bytes().replace(
        b"\r\n", b"\n"
    )


def differences(source: Path = SOURCE_DIR, target: Path = TARGET_DIR) -> list[str]:
    """Rutas relativas que faltan, sobran o difieren en la copia."""

    source_files = _files(source)
    target_files = _files(target)
    problems = []
    for relative, path in source_files.items():
        if relative not in target_files:
            problems.append(f"falta: {relative}")
        elif not _same_content(path, target_files[relative]):
            problems.append(f"difiere: {relative}")
    for relative in target_files:
        if relative not in source_files:
            problems.append(f"sobra: {relative}")
    return problems


def sync(source: Path = SOURCE_DIR, target: Path = TARGET_DIR) -> list[str]:
    """Deja `target` igual a `source`. Devuelve las rutas tocadas."""

    source_files = _files(source)
    target_files = _files(target)
    touched = []
    for relative, path in source_files.items():
        destination = target / relative
        if relative in target_files and _same_content(path, destination):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        touched.append(relative)
    for relative, path in target_files.items():
        if relative not in source_files:
            path.unlink()
            touched.append(relative)
    # Carpetas que quedaron vacías tras borrar sobrantes.
    if target.is_dir():
        for directory in sorted(target.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    return touched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; falla si .claude/skills/ difiere de .agents/skills/.",
    )
    args = parser.parse_args(argv)

    if args.check:
        problems = differences()
        if problems:
            print(".claude/skills/ no coincide con .agents/skills/:")
            for problem in problems:
                print(f"  - {problem}")
            print("Correr: python scripts/ai/sync_skills.py")
            return 1
        print("Skills sincronizadas.")
        return 0

    touched = sync()
    print(f"Skills sincronizadas ({len(touched)} archivo(s) actualizados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
