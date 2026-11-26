# Cambio: base de audiencias y alcance por tablero (#2912)

## Alcance

Se agregan audiencias, membresías y concesiones individuales o por audiencia, junto al cálculo de alcance por tablero. El rol de audiencia se limita a tableros y no modifica los roles generales del usuario. La decisión se registra en `docs/registro/decisiones/2026-11-26-2912-audiencias-alcance.md`.

## Comportamiento

Las concesiones de un tablero se acumulan; nacional, provincias y CDI se conservan por separado. No se infiere que un CDI autorice una provincia completa. Usuarios inactivos y tableros inactivos no reciben alcance nuevo. Las membresías se modifican por los métodos explícitos del modelo para que alta y baja pasen por auditoría; las concesiones se guardan completas, no con `update_fields`. La base valida sujeto, forma del alcance y la clave que asegura unicidad.

Los CDI requieren un validador de la vertical: sin él no conceden acceso. La implementación no conecta el cálculo a rutas ni datos y no modifica la política heredada. Los permisos existentes sin alcance confiable conservan su política previa hasta su revisión.

## Verificación

Pruebas con SQLite y MySQL 8 sintéticos cubren unión, separación entre tableros, datos inválidos, duplicados, revocación, validador CDI y auditoría de membresía y concesión. Revisión independiente reprodujo tres fallos y verificó sus correcciones. Se probó la migración en bases locales descartables, sin datos reales. El primer intento MySQL aplicó `dashboard` pero falló en post-migración por el estado inicial de `auth`; se actualizaron sus migraciones y se repitió la verificación.

## Limitaciones

Faltan el front, la administración segura, el validador CDI real, los permisos de gestión, la aplicación por ruta, consultas y exportaciones, y la coordinación con Datos. Operaciones masivas que omiten señales no constituyen un camino auditado; la administración debe usar los métodos y escrituras auditables. El cálculo no es garantía de aislamiento hasta que cada tablero lo aplique antes de entregar datos. No hubo publicación ni despliegue.
