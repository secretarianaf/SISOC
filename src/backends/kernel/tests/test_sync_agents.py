"""Generación y verificación de la configuración para agentes (src/scripts/ai/sync_agents.py)."""

import json

from scripts.ai import sync_agents


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _skill(base, name, description):
    _write(
        base / name / "SKILL.md",
        f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n# {name}\n".encode(),
    )


GUARDRAILS = b"""
[claude]
worktree_base_ref = "fresh"

[[comando]]
decision = "bloquear"
motivo = "Reescribe la historia."
prefijos = ["git push --force"]
solo_claude = ["git push * --force*"]

[[comando]]
decision = "confirmar"
motivo = "Pierde trabajo local."
prefijos = ["git reset --hard"]

[[archivo]]
decision = "bloquear"
motivo = "Credenciales."
patrones = ["**/.env"]
"""


# --- Skills: copia ------------------------------------------------------------


def test_sync_copia_actualiza_y_borra_sobrantes(tmp_path):
    source = tmp_path / ".agents" / "skills"
    target = tmp_path / ".claude" / "skills"
    _write(source / "a" / "SKILL.md", b"nueva\n")
    _write(source / "b" / "SKILL.md", b"version 2\n")
    _write(target / "b" / "SKILL.md", b"version 1\n")
    _write(target / "vieja" / "SKILL.md", b"borrar\n")

    assert sync_agents.skill_differences(source, target) == [
        "falta: a/SKILL.md",
        "difiere: b/SKILL.md",
        "sobra: vieja/SKILL.md",
    ]

    touched = sync_agents.sync_skills(source, target)

    assert sorted(touched) == ["a/SKILL.md", "b/SKILL.md", "vieja/SKILL.md"]
    assert (target / "a" / "SKILL.md").read_bytes() == b"nueva\n"
    assert (target / "b" / "SKILL.md").read_bytes() == b"version 2\n"
    assert not (target / "vieja").exists()
    assert sync_agents.skill_differences(source, target) == []


def test_copia_ignora_diferencias_de_fin_de_linea(tmp_path):
    source = tmp_path / ".agents" / "skills"
    target = tmp_path / ".claude" / "skills"
    _write(source / "a" / "SKILL.md", b"linea 1\nlinea 2\n")
    _write(target / "a" / "SKILL.md", b"linea 1\r\nlinea 2\r\n")

    assert sync_agents.skill_differences(source, target) == []


# --- Skills: descripción ------------------------------------------------------


def test_skill_valida_no_reporta_problemas(tmp_path):
    _skill(tmp_path, "mi-skill", "Hace algo. Usar cuando haya que hacer algo.")

    assert sync_agents.skill_problems(tmp_path) == []


def test_skill_sin_disparador_ni_nombre_correcto_se_reporta(tmp_path):
    _write(
        tmp_path / "mi-skill" / "SKILL.md",
        b"---\nname: otro\ndescription: Hace algo.\n---\n",
    )

    assert sync_agents.skill_problems(tmp_path) == [
        "mi-skill: `name` debe ser 'mi-skill' (es 'otro')",
        "mi-skill: la `description` debe decir cuándo usarla ('Usar cuando ...')",
    ]


def test_skill_con_descripcion_larga_o_sin_skill_md_se_reporta(tmp_path):
    _skill(tmp_path, "larga", "Usar cuando " + "x" * sync_agents.DESCRIPTION_MAX_CHARS)
    (tmp_path / "vacia").mkdir()

    problems = sync_agents.skill_problems(tmp_path)

    assert problems[0].startswith("larga: la `description` tiene ")
    assert problems[1] == "vacia: falta SKILL.md"


# --- Guardrails ---------------------------------------------------------------


def test_guardrails_generan_settings_de_claude(tmp_path):
    source = tmp_path / "guardrails.toml"
    source.write_bytes(GUARDRAILS)

    settings = json.loads(
        sync_agents.render_claude_settings(sync_agents.load_guardrails(source))
    )

    assert settings == {
        "worktree": {"baseRef": "fresh"},
        "permissions": {
            "deny": [
                "Bash(git push --force)",
                "Bash(git push --force *)",
                "Bash(git push * --force*)",
                "Read(./**/.env)",
                "Edit(./**/.env)",
            ],
            "ask": ["Bash(git reset --hard)", "Bash(git reset --hard *)"],
        },
    }


def test_guardrails_generan_reglas_de_codex_sin_patrones_solo_claude(tmp_path):
    source = tmp_path / "guardrails.toml"
    source.write_bytes(GUARDRAILS)

    rules = sync_agents.render_codex_rules(sync_agents.load_guardrails(source))

    assert rules.startswith("# GENERADO por src/scripts/ai/sync_agents.py")
    assert (
        'pattern = ["git", "push", "--force"],\n'
        '    decision = "forbidden",\n'
        '    justification = "Reescribe la historia.",'
    ) in rules
    assert 'pattern = ["git", "reset", "--hard"],\n    decision = "prompt",' in rules
    assert "*" not in rules
    assert ".env" not in rules


def test_decision_invalida_falla(tmp_path):
    source = tmp_path / "guardrails.toml"
    source.write_bytes(
        b'[[comando]]\ndecision = "quizas"\nmotivo = "x"\nprefijos = ["ls"]\n'
    )

    try:
        sync_agents.load_guardrails(source)
    except ValueError as error:
        assert "quizas" in str(error)
    else:
        raise AssertionError("se esperaba ValueError")


def test_guardrail_differences_detecta_falta_y_desvio(tmp_path):
    generado = tmp_path / "settings.json"
    faltante = tmp_path / "sisoc.rules"
    generado.write_bytes(b"editado a mano\r\n")

    problems = sync_agents.guardrail_differences(
        {generado: "original\n", faltante: "x\n"}
    )

    assert problems == [f"difiere: {generado}", f"falta: {faltante}"]


def test_check_falla_con_mensaje_si_algo_difiere(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sync_agents, "skill_differences", lambda: ["falta: a/SKILL.md"])
    monkeypatch.setattr(sync_agents, "guardrail_differences", lambda expected: [])
    monkeypatch.setattr(sync_agents, "skill_problems", lambda: [])

    assert sync_agents.main(["--check"]) == 1
    output = capsys.readouterr().out
    assert "skills: falta: a/SKILL.md" in output
    assert "python src/scripts/ai/sync_agents.py" in output
