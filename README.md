# SISOC

Sistema de gestión basado en **Django** y **MySQL**, desplegable mediante **Docker** y **Docker Compose**.  
Cada aplicación del repositorio representa un módulo funcional (ej. `comedores`, `relevamientos`, `users`). El código vive en `src/` (ver [Estructura de Carpetas](#estructura-de-carpetas)).

> Documentación organizada: ver `docs/indice.md` para el índice y referencias detalladas.
> Setup y operación: `docs/operacion/instalacion.md`, `docs/operacion/infraestructura.md` y `docs/operacion/comandos_administracion.md`.

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)  
2. [Requisitos Previos](#requisitos-previos)  
3. [Despliegue Local](#despliegue-local)  
4. [Estructura de Carpetas](#estructura-de-carpetas)  
5. [Formateo y Estilo de Código](#formateo-y-estilo-de-código)  
6. [Variables de Entorno](#variables-de-entorno)  
7. [Tests Automáticos](#tests-automáticos)  
8. [Buenas Prácticas](#buenas-prácticas)  
9. [API](#api)  
10. [Tecnologías Utilizadas](#tecnologías-utilizadas)  
11. [Despliegues](#despliegues)  
12. [Changelog](#changelog)  
13. [Contribución](#contribución)

---

## Arquitectura General

- **Backend**: Django  
- **Base de datos**: MySQL  
- **Contenedores**: Docker + Docker Compose  
- **Front-end**: templates Django (HTML, CSS, JS, Bootstrap) y front v2 en React (`src/frontends/`)  
- **Tests**: pytest  

---

## Requisitos Previos

- [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/) instalados.  
- Python 3.11+ (solo si se ejecuta fuera de contenedores).  
- VSCode recomendado con extensión **Python** y **Docker**.  

---

## Despliegue Local

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/secretarianaf/SISOC.git
   cd SISOC
   ```
2. Copiar `.env.example` a `.env` y completar la configuración local según `docs/operacion/instalacion.md`.
3. (Opcional) Colocar un dump en `./docker/mysql/local-dump.sql`.
4. Levantar servicios:
   ```bash
   docker compose up
   ```
5. Acceder a la app en [http://localhost:8001](http://localhost:8001) (valor por defecto de `DOCKER_DJANGO_PORT_FORWARD` en `.env.example`).

`docker-compose.yml` queda reservado para desarrollo/local y es el único compose versionado que levanta `mysql`.

## Reiniciar base de datos con nuevo dump
```bash
docker compose down
docker volume rm sisoc_mysql_data
# colocar nuevo dump en ./docker/mysql/local-dump.sql
docker compose up
```

## Debug con VSCode
- Iniciar servicios con `docker compose up`.
- Seleccionar la configuración `Django in Docker` en el panel de debugging.  

---

## Estructura de Carpetas

La raíz tiene solo configuración de herramientas, puntos de entrada y carpetas con un propósito.
Decisión: `docs/registro/decisiones/2026-10-02-estructura-src-backends.md`.

| Carpeta | Propósito |
|-|-|
| `src/backends/` | Código Django. `src/backends/config/` es el proyecto (settings, urls, registro de backends); `src/backends/kernel/` es el código común con templates, estáticos y tests compartidos; `src/backends/sisoc_core/` es el cluster de Comedores y servicios del core. Cada vertical (pas, cdi, cdf, celiaquia, dispositivos, vat, vpsl) tiene su carpeta y contenedor. Guía: `docs/desarrollo/verticales_independientes.md`. |
| `src/frontends/` | Workspace npm del Front v2: `apps/<modulo>/`, `packages/`, opciones base de TypeScript en `src/frontends/config/` y `e2e/`. Las entradas de npm, TypeScript, ESLint, Vitest y Playwright permanecen en su ubicación convencional para conservar su detección automática. |
| `docs/` | Documentación: índice en `docs/indice.md`, registros por trimestre en `docs/registro/`. |
| `docker/` | Dockerfile, entrypoint y `docker/compose/` con los overrides de deploy, Celery, Codex y fronts. |
| `requirements/` | Dependencias Python (`all.txt` = base + dev + test). |
| `src/scripts/` | Scripts operativos (`operacion/`, `infra/`), de CI (`ci/`), de arquitectura, frontend (`src/scripts/frontends/`), GitHub (`github/`) y agentes (`ai/`). |
| `.github/` | Workflows de CI/CD y plantillas. |
| `.agents/skills/` | Skills del repo (fuente). `.claude/skills/` es una copia generada (`docs/ia/SKILLS.md`). |
| `.claude/`, `.codex/` | Configuración de Claude Code y Codex. |
| `.vscode/` | Configuración compartida de VS Code y del debugger. |

Archivos de la raíz: `manage.py` (entrada Django), `conftest.py` (fixtures globales de pytest),
`docker-compose.yml` (stack local), `README.md`, `AGENTS.md` y `CLAUDE.md` (guías para agentes),
`CHANGELOG.md` y la configuración de herramientas (`pytest.ini`, `pyproject.toml`, `.pylintrc`,
`.importlinter*`, `.djlintrc`, `.gitleaks*`, `.editorconfig`, …).

Dentro de cada app Django: `<app>/templates/`, `<app>/static/custom/` (estáticos de un solo vertical, con la
misma ruta pública `custom/...`) y `tests/`.

---

## Formateo y Estilo de Código

Antes de un **Pull Request**, ejecutar:

```bash
# Linter (Se debe resolver a mano; el comando exacto del CI está en .github/workflows/lint.yml)
pylint src/backends/config/*.py src/backends/*/*/*.py --rcfile=.pylintrc

# Formateo Python (Automagico)
black .

# Formateo Django Templates (Aveces automagico, a veces no)
djlint . --configuration=.djlintrc --reformat
```

---

## Variables de Entorno

Ejemplo y defaults en `.env.example`.
Para más detalle operativo: `docs/operacion/instalacion.md`.

---

## Tests Automáticos

Ejecutar:
```bash
docker compose exec django pytest -n auto
```

Referencia CI actual:
- `tests.yml` corre `smoke`, `migrations_check` y, en PRs, `pytest` con cobertura + `mysql_compat`.
- `lint.yml` corre `encoding_check`, `skills_sync`, `black`, `djlint` y `pylint`.

---

## Buenas Prácticas

1. **Estilo de código**  
   - Python → `snake_case`  
   - JavaScript → `CamelCase`  

2. **Arquitectura Django**  
   - **Modelo**: docstring + `verbose_name` → evitar redundancia.  
   - **Vista**: usar **Class Based Views**, sin lógica de negocio.  
   - **Template**: evitar consultas y mantener simple.  

3. **Organización interna**  
   - Archivos ordenados por módulo.  
   - Servicios en `services/` por modelo.  
   - Templates separados por entidad.  

4. **Commits**  
   Usar formato consistente:  
   ```
   feat(comedores): nueva funcionalidad
   fix(relevamientos): corregir bug
   refactor(users): limpiar servicios
   ```

   Los cambios importantes deben registrar su contexto en `docs/registro/`.

---

## API

Documentación Postman:  
[API SISOC](https://documenter.getpostman.com/view/14921866/2sAXxMfDXf#01ac9db5-a6b5-4b20-9e8c-973e38884f17)
No es la mejor documentacion. En caso de dudas, consultar con Juani (Tech lead de SISOC) o Andy (Dueño de GESCOM)

Además, el repo expone schema OpenAPI en `/api/schema/`, Swagger en `/api/docs/` y Redoc en `/api/redoc/`.
Ejemplo de request:
```bash
curl -X GET http://localhost:8001/api/comedores/ \
  -H "Authorization: Api-Key <API_KEY>"
```

---

## Despliegues

##Ciclo quincenal de releases
- **Semana 0 (jueves)** → abrir branch `development`.  
- **Semana 2 (lunes, freeze)** → congelar `development`, crear tag `YY.MM.DD-rc1`.  
- **Semana 2 (miércoles noche)** → deploy a PRD si QA aprueba último `rcX`.  

Para detalle operativo vigente de entornos, compose y release, usar `docs/operacion/infraestructura.md`.

##Checklist
- [ ] Branch `development` congelada sin features nuevos  
- [ ] Backup válido de DB  
- [ ] Tag final creado en `development`  
- [ ] Probado con base similar a PRD  
- [ ] Testeado en QA ese mismo tag  
- [ ] QA aprobó el tag  
- [ ] Merge limpio a `main`  
- [ ] Changelog actualizado  
- [ ] Migraciones reversibles/controladas  
- [ ] Equipo notificado  
- [ ] Último tag estable guardado para rollback  
- [ ] Squash de migraciones estables  

---

## Changelog

`CHANGELOG.md`

Los usuarios del sistema pueden consultar las novedades desde la opción **"Novedades del sistema"** en el menú lateral del backoffice.

---

## Contribución

1. Crear una branch desde `development`.  
2. Commit siguiendo el estándar definido.  
3. Abrir **Pull Request** a `development`.  
4. Pasar linters y tests antes del PR.  
5. Revisión de al menos otro dev antes del merge.  

---
