# AGENTS.md: front v2 (React)

Se suma a `AGENTS.md` de la raiz. Guia: `docs/implementaciones/frontend_v2.md`; si una tarea necesita romper una de sus reglas, se discute en la epica antes de implementar, no en el PR.

- Una app no importa de otra app: lo compartido va en `packages/`. El front no importa nada del back ni lee archivos de apps Django.
- MUI, no Tailwind. El tema (`buildTheme`) vive solo en `@sisoc/ui`: las apps no redefinen colores.
- Todo `/v2/` exige sesion Django. El front habla con el back solo por API; no usa templates ni el `api.py` de las apps.
- El menu viejo no enlaza a `/v2/` salvo decision explicita.
- Los tipos de la API se generan desde los esquemas OpenAPI de `packages/api/`; no editar los archivos generados a mano.
