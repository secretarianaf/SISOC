# AGENTS.md: backends Django

Se suma a `AGENTS.md` de la raiz. Guia de verticales: `docs/desarrollo/verticales_independientes.md`.

- El kernel no importa core ni verticales; un servicio no importa a otro, tampoco su `api.py`.
- Registrar prefijos en `src/backends/config/backends.json` y regenerar `src/backends/config/url_registry.json`.
- Resolver archivos por app o `__file__`, nunca por `BASE_DIR` + nombre de app.
- Comandos del grafo completo y `collectstatic` corren en el migrador, no en la web de deploy.
- La logica de negocio vive en `services/` de la app; views y templates no concentran reglas de dominio.
- Views nuevas: class-based. Las function-based existentes no se migran salvo pedido.
- Si cambia una API que consume el front v2, regenerar su esquema OpenAPI en `src/frontends/packages/api/` (CI compara el archivo).
