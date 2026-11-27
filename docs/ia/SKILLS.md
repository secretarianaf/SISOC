# Skills del repo

Las skills son instrucciones empaquetadas para un tipo de tarea (por ejemplo, el
tema de color institucional o el trabajo de UI). Las usan Codex y Claude Code.

## Dónde viven

| Carpeta | Qué es | Quién la lee |
|-|-|-|
| `.agents/skills/<nombre>/SKILL.md` | **Fuente**: se edita acá | Codex |
| `.claude/skills/<nombre>/SKILL.md` | Copia generada: **no se edita a mano** | Claude Code |

La copia la genera `src/scripts/ai/sync_agents.py`, que también genera los guardrails (`docs/ia/GUARDRAILS.md`). No se usan symlinks porque se
rompen en Windows con `core.symlinks=false` (ver
`docs/registro/decisiones/2026-10-02-estructura-src-backends.md`).

## Agregar o editar una skill

1. Crear o editar `.agents/skills/<nombre>/SKILL.md`. El nombre va en
   minúsculas con guiones y coincide con el `name` del frontmatter.
2. El archivo empieza con un frontmatter YAML con `name` y `description`. La
   `description` dice qué hace la skill y **cuándo usarla**, con la frase
   `Usar cuando ...`, en 250 caracteres como máximo. Es lo único que el agente
   lee para decidir si la carga: `AGENTS.md` no lista skills.

   ```markdown
   ---
   name: mi-skill
   description: >
     Qué hace. Usar cuando <situación concreta que la dispara>.
   ---

   # Título

   Instrucciones...
   ```

3. Si la skill necesita archivos de apoyo (plantillas, ejemplos), ponerlos en
   la misma carpeta y referenciarlos desde `SKILL.md`. Las skills de proceso
   llevan un `ejemplo.md` con un caso real del repo.
   Una skill no agrega reglas: aplica una guía de `docs/` y la cita como fuente.
4. Sincronizar y commitear las dos carpetas:

   ```bash
   python src/scripts/ai/sync_agents.py
   git add .agents/skills .claude/skills
   ```

Para borrar una skill, borrar su carpeta en `.agents/skills/` y correr el
script: también la saca de `.claude/skills/`.

## Validación

`python src/scripts/ai/sync_agents.py --check` falla si la copia difiere de la
fuente (sin distinguir CRLF/LF), si una skill no tiene `name` igual a su carpeta
o si su `description` no dice `Usar cuando` o supera los 250 caracteres. Corre en
`src/scripts/ai/preflight.sh` y en CI (job `agents_sync` de
`.github/workflows/lint.yml`), que **avisa pero no bloquea** el merge.

## Skills actuales

La lista es el contenido de `.agents/skills/`. Cada `description` dice qué hace
la skill y cuándo usarla; no se repite acá para que no se desactualice.
