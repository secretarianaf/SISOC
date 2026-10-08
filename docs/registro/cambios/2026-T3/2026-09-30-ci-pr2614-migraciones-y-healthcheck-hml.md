# CI y deploy HML para la promoción a main

La integración de `main` con `homologacion` dejaba dos migraciones hoja en
`users`: permisos por sección del ABM y carga de roles territoriales PNUD. El
arranque de Django en desarrollo ejecuta `makemigrations`, que falla ante ese
grafo ambiguo; por eso fallaban `migrations_check`, `mysql_compat` y luego
`deploy_guard` en el PR de promoción.

Se agregó una migración de unión sin operaciones para declarar que ambas ramas
de datos/schema son aplicables antes de continuar. El overlay de deploy de HML
también eleva de 5 a 10 minutos el período de gracia del healthcheck Django,
igualándolo al compose base, que necesita ese margen para terminar migraciones,
fixtures y el arranque web.

El healthcheck de HML vuelve a correr automáticamente al actualizar
`homologacion`. La salida de la migración de roles debe revisarse para detectar
usuarios no encontrados. Las migraciones de base de datos no se revierten con
el rollback de código. La validación del certificado TLS de HML es independiente
de este cambio.
