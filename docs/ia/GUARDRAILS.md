# Guardrails para agentes

Límites que la herramienta aplica sola, sin depender de que el agente lea una
regla. Valen igual para Claude Code y Codex.

## Cómo funciona

| Archivo | Qué es | Se edita |
|-|-|-|
| `.agents/guardrails.toml` | **Fuente única**: cada límite con su decisión y su motivo | Sí, a mano |
| `.claude/settings.json` | `permissions.deny` / `permissions.ask` de Claude Code | No: generado |
| `.codex/rules/sisoc.rules` | `prefix_rule` de Codex (`forbidden` / `prompt`) | No: generado |

Después de editar la fuente:

```bash
python src/scripts/ai/sync_agents.py
git add .agents/guardrails.toml .claude/settings.json .codex/rules/sisoc.rules
```

`python src/scripts/ai/sync_agents.py --check` avisa si los generados no
coinciden con la fuente. En CI corre como `agents_sync` y **no bloquea** el merge.

## Decisiones

- **bloquear**: el comando no se ejecuta. Para lo irreversible o lo que sale del
  entorno local: push forzado o a ramas compartidas, release o workflows,
  `--no-verify`, `ssh`, `scp`, `mysqldump` y `manage.py flush`.
- **confirmar**: un humano aprueba cada vez. Para lo destructivo pero local
  (`git reset --hard`, `git clean`, `rm -rf`, `docker compose down -v`,
  instalar dependencias) y para `gh pr merge`, que la skill `preparar-deploy`
  necesita: el agente puede proponer el merge, pero lo aprueba una persona.

La lista completa y el motivo de cada regla están en la fuente.

## Diferencias entre herramientas

| Límite | Claude Code | Codex |
|-|-|-|
| Comandos por prefijo (`prefijos`) | Sí | Sí |
| Comandos con comodín (`solo_claude`) | Sí | No: solo prefijos exactos |
| Leer o editar `.env`, `*.sql`, `*.dump` | Sí | No: Codex no bloquea archivos por ruta |
| Worktrees desde el remoto (`worktree.baseRef`) | Sí | No aplica |

Codex carga `.codex/rules/` solo si el proyecto es de confianza ("trusted"), y sus
reglas son experimentales. Verificar una regla con:

```bash
codex execpolicy check --rules .codex/rules/sisoc.rules -- git push origin main
```

## Límites conocidos

- Las reglas comparan prefijos de comando. Protegen contra errores, no contra un
  intento deliberado de esquivarlas (por ejemplo, `bash -c "..."`).
- En Claude Code un `deny` del proyecto gana sobre cualquier `allow` local: para
  hacer algo bloqueado hay que cambiar la fuente en un PR o que lo haga un humano.
- Instalar dependencias pide confirmación también sin paquete (`npm install`),
  porque Codex no distingue un comando con argumentos de uno sin ellos.
- Las preferencias personales (modelo, permisos de comodidad como
  `docker compose *`) van en `.claude/settings.local.json`, ignorado por Git.
