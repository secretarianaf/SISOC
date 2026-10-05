# Skills del repo

Las skills son instrucciones empaquetadas para un tipo de tarea (por ejemplo, el
tema de color institucional o el trabajo de UI). Las usan Codex y Claude Code.

## Dónde viven

| Carpeta | Qué es | Quién la lee |
|-|-|-|
| `.agents/skills/<nombre>/SKILL.md` | **Fuente**: se edita acá | Codex |
| `.claude/skills/<nombre>/SKILL.md` | Copia generada: **no se edita a mano** | Claude Code |

La copia la genera `scripts/ai/sync_skills.py`. No se usan symlinks porque se
rompen en Windows con `core.symlinks=false` (ver
`docs/registro/decisiones/2026-10-02-estructura-src-backends.md`).

## Agregar o editar una skill

1. Crear o editar `.agents/skills/<nombre>/SKILL.md`. El nombre va en
   minúsculas con guiones y coincide con el `name` del frontmatter.
2. El archivo empieza con un frontmatter YAML con `name` y `description`. La
   `description` dice qué hace la skill y **cuándo usarla**: es lo que el
   agente lee para decidir si la carga.

   ```markdown
   ---
   name: mi-skill
   description: >
     Qué hace y cuándo usarla, en una o dos oraciones.
   ---

   # Título

   Instrucciones...
   ```

3. Si la skill necesita archivos de apoyo (plantillas, ejemplos), ponerlos en
   la misma carpeta y referenciarlos desde `SKILL.md`.
4. Sincronizar y commitear las dos carpetas:

   ```bash
   python scripts/ai/sync_skills.py
   git add .agents/skills .claude/skills
   ```

Para borrar una skill, borrar su carpeta en `.agents/skills/` y correr el
script: también la saca de `.claude/skills/`.

## Validación

- `python scripts/ai/sync_skills.py --check` falla si la copia difiere de la
  fuente (sin distinguir CRLF/LF).
- Corre en CI (`skills_sync` en `.github/workflows/lint.yml`), en
  `scripts/ai/preflight.sh` y en el test
  `src/backends/kernel/tests/test_sync_skills.py`.

## Skills actuales

- `tema-verde-institucional`: paleta y tema de Material UI del diseño verde
  institucional (claro y oscuro). Origen: adjunto de #2639.
- `frontend-ui-ux`: diseño e implementación de UI/UX en templates Django, CSS
  y JS. Convertida desde el antiguo `frontend-ui-ux.agent.md`.
