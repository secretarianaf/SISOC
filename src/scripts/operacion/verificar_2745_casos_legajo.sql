-- Verificación previa al deploy del #2745 (legajo de Organización por programa).
-- Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
--
-- Solo lectura (SELECT). Correr en homologación y producción ANTES de desplegar
-- la migración 0004 (carga inicial). Usa las tablas actuales, así que calcula lo
-- que haría la carga inicial: programas de la organización = programas de todos
-- sus comedores, incluidos los dados de baja.
--
-- Resultado esperado: las consultas 1 y 2 no devuelven filas. Si devuelven,
-- el legajo nuevo no tiene lugar para esos casos (definición del área usuaria
-- del 23/10/2026): revisar con el área antes de desplegar.
--
-- Los nombres se comparan con LIKE: con la intercalación por defecto de
-- MySQL 8 (utf8mb4_0900_ai_ci) no distinguen mayúsculas ni acentos.

-- 1. Organizaciones que recibirían un programa que no es uno de los tres del
--    legajo (Alimentar Comunidad, Línea Secos, Línea Tradicional).
SELECT
    o.id AS organizacion_id,
    o.nombre AS organizacion,
    p.id AS programa_id,
    p.nombre AS programa,
    COUNT(c.id) AS comedores,
    SUM(c.deleted_at IS NOT NULL) AS comedores_dados_de_baja
FROM comedores_comedor c
JOIN organizaciones_organizacion o ON o.id = c.organizacion_id
JOIN comedores_programas p ON p.id = c.programa_id
WHERE NOT (
    p.nombre LIKE 'alimentar comunidad'
    OR (
        p.nombre LIKE '%abordaje comunitario%'
        AND (p.nombre LIKE '%linea secos%' OR p.nombre LIKE '%linea tradicional%')
    )
)
GROUP BY o.id, o.nombre, p.id, p.nombre
ORDER BY o.id, p.id;

-- 2. Organizaciones con documentación cargada que no recibirían Alimentar
--    Comunidad (ningún comedor, ni dado de baja, con ese programa).
SELECT
    o.id AS organizacion_id,
    o.nombre AS organizacion,
    COUNT(a.id) AS documentos_vigentes
FROM organizaciones_archivoorganizacion a
JOIN organizaciones_organizacion o ON o.id = a.organizacion_id
WHERE a.deleted_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM comedores_comedor c
      JOIN comedores_programas p ON p.id = c.programa_id
      WHERE c.organizacion_id = o.id
        AND p.nombre LIKE 'alimentar comunidad'
  )
GROUP BY o.id, o.nombre
ORDER BY o.id;

-- 3. Resumen (para el registro del deploy).
SELECT
    (SELECT COUNT(DISTINCT c.organizacion_id)
       FROM comedores_comedor c
       JOIN comedores_programas p ON p.id = c.programa_id
      WHERE NOT (
          p.nombre LIKE 'alimentar comunidad'
          OR (
              p.nombre LIKE '%abordaje comunitario%'
              AND (p.nombre LIKE '%linea secos%' OR p.nombre LIKE '%linea tradicional%')
          )
      )) AS caso_programa_fuera_de_los_tres,
    (SELECT COUNT(DISTINCT a.organizacion_id)
       FROM organizaciones_archivoorganizacion a
      WHERE a.deleted_at IS NULL
        AND NOT EXISTS (
            SELECT 1
            FROM comedores_comedor c
            JOIN comedores_programas p ON p.id = c.programa_id
            WHERE c.organizacion_id = a.organizacion_id
              AND p.nombre LIKE 'alimentar comunidad'
        )) AS caso_documentos_sin_alimentar;
