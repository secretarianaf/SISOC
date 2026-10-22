# Boundaries de servicios y módulos

Guía vigente: [Verticales independientes](../desarrollo/verticales_independientes.md).
Las reglas cortas están en `AGENTS.md` ("Verticales independientes"); acá solo
lo que agrega al diseñar un módulo nuevo o una dependencia entre dominios.

- SISOC tiene core de entrada y backends registrados y una DB compartida; no un único deployable.
- Clasificar el cambio por dueño (kernel, `sisoc_core`, vertical o frontend) antes de diseñar.
- Dentro de un mismo servicio, reutilizar APIs/services públicos y patrones existentes.
- Una FK al kernel autorizado no elimina la coordinación de esquema y migraciones.
- No ocultar dependencias con SQL, signals o imports dinámicos; revisar compatibilidad.
- Aplicar el checklist que corresponda de la guía (skill `verticales-checklist`).
- Estado de las extracciones de #2641 (C0–C4) y su evidencia: `docs/registro/cambios/2026-T4/`.
- Antecedente histórico: `docs/registro/decisiones/2026-07-21-modulos-nuevos-extraibles.md`.
