"""Genera y verifica la configuración para agentes de IA desde sus fuentes.

Fuentes (se editan a mano):
    .agents/skills/        skills del repo (las lee Codex)
    .agents/guardrails.toml límites de comandos y archivos

Generados (no se editan a mano):
    .claude/skills/          copia de las skills para Claude Code
    .claude/settings.json    guardrails de Claude Code (permissions)
    .codex/rules/sisoc.rules guardrails de Codex (prefix_rule)

Uso:
    python src/scripts/ai/sync_agents.py          # genera todo
    python src/scripts/ai/sync_agents.py --check  # exit 1 si algo difiere o una skill es inválida

Solo stdlib. Ver docs/ia/GUARDRAILS.md y docs/ia/SKILLS.md.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_SOURCE = REPO_ROOT / ".agents" / "skills"
SKILLS_TARGET = REPO_ROOT / ".claude" / "skills"
GUARDRAILS_SOURCE = REPO_ROOT / ".agents" / "guardrails.toml"
CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
CODEX_RULES = REPO_ROOT / ".codex" / "rules" / "sisoc.rules"
IGNORED_NAMES = {"__pycache__", ".DS_Store"}

DESCRIPTION_MAX_CHARS = 250
DESCRIPTION_TRIGGER = "Usar cuando"
CODEX_DECISIONS = {"bloquear": "forbidden", "confirmar": "prompt"}
CLAUDE_BUCKETS = {"bloquear": "deny", "confirmar": "ask"}
GENERATED_HEADER = (
    "# GENERADO por src/scripts/ai/sync_agents.py desde .agents/guardrails.toml.\n"
    "# No editar a mano: editar la fuente y volver a generar.\n"
)


# --- Skills: copia .agents/skills/ -> .claude/skills/ -----------------------


def _files(base: Path) -> dict[str, Path]:
    """Archivos bajo `base`, por ruta relativa POSIX."""

    if not base.is_dir():
        return {}
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file() and not IGNORED_NAMES.intersection(path.parts)
    }


def _normalized(data: bytes) -> bytes:
    # Sin distinguir CRLF/LF: con core.autocrlf el checkout de Windows puede
    # cambiar los finales de línea de un solo lado.
    return data.replace(b"\r\n", b"\n")


def _same_content(left: Path, right: Path) -> bool:
    return _normalized(left.read_bytes()) == _normalized(right.read_bytes())


def skill_differences(
    source: Path = SKILLS_SOURCE, target: Path = SKILLS_TARGET
) -> list[str]:
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


def sync_skills(
    source: Path = SKILLS_SOURCE, target: Path = SKILLS_TARGET
) -> list[str]:
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
    if target.is_dir():
        for directory in sorted(target.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    return touched


# --- Skills: validación del frontmatter -------------------------------------


def _frontmatter(text: str) -> dict[str, str]:
    """Lee `name` y `description` del frontmatter YAML (subconjunto simple).

    Soporta valores en una línea (con o sin comillas) y bloques `>` / `|`.
    """

    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    fields: dict[str, str] = {}
    key = None
    block: list[str] = []
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            if key is not None:
                fields[key] = " ".join(block).strip()
            key, value = match.group(1), match.group(2).strip()
            block = [] if value in {">", "|", ">-", "|-"} else [value.strip("\"'")]
        elif key is not None:
            block.append(line.strip())
    if key is not None:
        fields[key] = " ".join(block).strip()
    return fields


def skill_problems(source: Path = SKILLS_SOURCE) -> list[str]:
    """Skills sin `name`/`description` válidos para que el agente las cargue."""

    problems = []
    if not source.is_dir():
        return problems
    for skill_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        label = skill_dir.name
        if not skill_file.is_file():
            problems.append(f"{label}: falta SKILL.md")
            continue
        fields = _frontmatter(skill_file.read_text(encoding="utf-8"))
        name = fields.get("name", "")
        description = fields.get("description", "")
        if name != label:
            problems.append(f"{label}: `name` debe ser '{label}' (es '{name}')")
        if not description:
            problems.append(f"{label}: falta `description`")
            continue
        if DESCRIPTION_TRIGGER not in description:
            problems.append(
                f"{label}: la `description` debe decir cuándo usarla "
                f"('{DESCRIPTION_TRIGGER} ...')"
            )
        if len(description) > DESCRIPTION_MAX_CHARS:
            problems.append(
                f"{label}: la `description` tiene {len(description)} caracteres "
                f"(máximo {DESCRIPTION_MAX_CHARS})"
            )
    return problems


# --- Guardrails: .agents/guardrails.toml -> Claude y Codex ------------------


def load_guardrails(source: Path = GUARDRAILS_SOURCE) -> dict:
    with source.open("rb") as handle:
        data = tomllib.load(handle)
    for rule in data.get("comando", []) + data.get("archivo", []):
        if rule.get("decision") not in CODEX_DECISIONS:
            raise ValueError(f"decision inválida en {source}: {rule.get('decision')!r}")
        if not rule.get("motivo"):
            raise ValueError(f"regla sin motivo en {source}: {rule}")
    return data


def render_claude_settings(data: dict) -> str:
    buckets: dict[str, list[str]] = {"deny": [], "ask": []}
    for rule in data.get("comando", []):
        bucket = buckets[CLAUDE_BUCKETS[rule["decision"]]]
        for prefix in rule.get("prefijos", []):
            bucket.extend([f"Bash({prefix})", f"Bash({prefix} *)"])
        bucket.extend(f"Bash({pattern})" for pattern in rule.get("solo_claude", []))
    for rule in data.get("archivo", []):
        bucket = buckets[CLAUDE_BUCKETS[rule["decision"]]]
        for pattern in rule.get("patrones", []):
            bucket.extend([f"Read(./{pattern})", f"Edit(./{pattern})"])
    settings: dict = {}
    base_ref = data.get("claude", {}).get("worktree_base_ref")
    if base_ref:
        settings["worktree"] = {"baseRef": base_ref}
    settings["permissions"] = {key: value for key, value in buckets.items() if value}
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def render_codex_rules(data: dict) -> str:
    blocks = [GENERATED_HEADER]
    for rule in data.get("comando", []):
        for prefix in rule.get("prefijos", []):
            tokens = ", ".join(json.dumps(token) for token in shlex.split(prefix))
            justification = json.dumps(rule["motivo"], ensure_ascii=False)
            blocks.append(
                "prefix_rule(\n"
                f"    pattern = [{tokens}],\n"
                f'    decision = "{CODEX_DECISIONS[rule["decision"]]}",\n'
                f"    justification = {justification},\n"
                ")\n"
            )
    return "\n".join(blocks)


def generated_files(source: Path = GUARDRAILS_SOURCE) -> dict[Path, str]:
    data = load_guardrails(source)
    return {
        CLAUDE_SETTINGS: render_claude_settings(data),
        CODEX_RULES: render_codex_rules(data),
    }


def guardrail_differences(expected: dict[Path, str]) -> list[str]:
    problems = []
    for path, content in expected.items():
        relative = (
            path.relative_to(REPO_ROOT).as_posix()
            if path.is_relative_to(REPO_ROOT)
            else str(path)
        )
        if not path.is_file():
            problems.append(f"falta: {relative}")
        elif _normalized(path.read_bytes()) != content.encode("utf-8"):
            problems.append(f"difiere: {relative}")
    return problems


def write_generated(expected: dict[Path, str]) -> None:
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; falla si algo generado difiere o una skill es inválida.",
    )
    args = parser.parse_args(argv)

    expected = generated_files()
    invalid_skills = skill_problems()

    if args.check:
        problems = (
            [f"skills: {p}" for p in skill_differences()]
            + [f"guardrails: {p}" for p in guardrail_differences(expected)]
            + [f"descripción: {p}" for p in invalid_skills]
        )
        if problems:
            print("La configuración para agentes no está al día:")
            for problem in problems:
                print(f"  - {problem}")
            print(
                "Corregir la fuente si hace falta y correr: python src/scripts/ai/sync_agents.py"
            )
            return 1
        print("Configuración para agentes al día.")
        return 0

    touched = sync_skills()
    write_generated(expected)
    print(f"Skills sincronizadas ({len(touched)} archivo(s)); guardrails generados.")
    for problem in invalid_skills:
        print(f"  aviso: {problem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
