# Boundaries de servicios y módulos

Guía vigente: [Verticales independientes](../desarrollo/verticales_independientes.md).
- SISOC tiene core de entrada, siete backends y una DB compartida; no un único deployable.
- Clasificar el cambio por dueño: kernel, sisoc_core, vertical o frontend.
- Kernel no importa core/verticales; un servicio no importa otro, tampoco su api.py.
- Dentro de un mismo servicio, reutilizar APIs/services públicos y patrones existentes.
- Entre servicios, usar contratos HTML/JSON/favoritos con sesión, permisos y fallback.
- Una FK al kernel autorizado no elimina la coordinación de esquema y migraciones.
- No ocultar dependencias con SQL, signals o imports dinámicos; revisar compatibilidad.
- URLs en registros; recursos por app; grafo completo/collectstatic en migrador.
- Cambiar de app conservando db_table y content type requiere migraciones de estado.
- Verificar contratos de imports, runtime/imagen aislada y plan de deploy real.
- Aplicar los cuatro checklists de la guía; las propuestas de #2641 siguen fuera de alcance.
- Antecedente histórico: `docs/registro/decisiones/2026-07-21-modulos-nuevos-extraibles.md`.
