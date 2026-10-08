"""Sincronización de skills de .agents/skills/ a .claude/skills/ (src/scripts/ai/sync_skills.py)."""

from scripts.ai import sync_skills


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_sync_copia_actualiza_y_borra_sobrantes(tmp_path):
    source = tmp_path / ".agents" / "skills"
    target = tmp_path / ".claude" / "skills"
    _write(source / "a" / "SKILL.md", b"nueva\n")
    _write(source / "b" / "SKILL.md", b"version 2\n")
    _write(target / "b" / "SKILL.md", b"version 1\n")
    _write(target / "vieja" / "SKILL.md", b"borrar\n")

    assert sync_skills.differences(source, target) == [
        "falta: a/SKILL.md",
        "difiere: b/SKILL.md",
        "sobra: vieja/SKILL.md",
    ]

    touched = sync_skills.sync(source, target)

    assert sorted(touched) == ["a/SKILL.md", "b/SKILL.md", "vieja/SKILL.md"]
    assert (target / "a" / "SKILL.md").read_bytes() == b"nueva\n"
    assert (target / "b" / "SKILL.md").read_bytes() == b"version 2\n"
    assert not (target / "vieja").exists()
    assert sync_skills.differences(source, target) == []


def test_check_ignora_diferencias_de_fin_de_linea(tmp_path):
    source = tmp_path / ".agents" / "skills"
    target = tmp_path / ".claude" / "skills"
    _write(source / "a" / "SKILL.md", b"linea 1\nlinea 2\n")
    _write(target / "a" / "SKILL.md", b"linea 1\r\nlinea 2\r\n")

    assert sync_skills.differences(source, target) == []


def test_las_skills_del_repo_estan_sincronizadas():
    """Si falla: correr `python src/scripts/ai/sync_skills.py` y commitear .claude/skills/."""

    assert sync_skills.differences() == []
