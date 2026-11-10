-- Verificación previa al deploy del #2745 (legajo de Organización por programa).
-- Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
--
-- Solo lectura (SELECT). Correr en homologación y producción ANTES de desplegar.
--
-- Consultas 1 a 3: antes de la migración 0004 (carga inicial). Usan las tablas
-- actuales, así que calculan lo que haría la carga inicial: programas de la
-- organización = programas de todos sus comedores, incluidos los dados de baja.
-- Resultado esperado: las consultas 1 y 2 no devuelven filas. Si devuelven,
-- el legajo nuevo no tiene lugar para esos casos (definición del área usuaria
-- del 23/10/2026): revisar con el área antes de desplegar.
--
-- Consulta 4: antes de la migración gestion_organizaciones 0005 (#2836), donde
-- ya existan las tablas de región del #2745 (llegaron con la 0002). Lista lo que
-- haría frenar la 0005 por no pisar datos del #2642. Resultado esperado: sin
-- filas. Si devuelve, resolver cada caso a mano antes de desplegar.
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

-- 4. Casos que frenarían la migración 0005 (RegionNoCopiable). Replica sus
--    dos controles; los catálogos del kernel se cruzan por nombre (único),
--    igual que la migración.
--    a) Subzona en uso que en el kernel ya pertenece a otra región.
SELECT
    'subzona_de_otra_region' AS caso,
    NULL AS organizacion_id,
    sp.nombre AS valor_2745,
    rk.nombre AS valor_2642
FROM gestion_organizaciones_subzonaabordaje sp
JOIN gestion_organizaciones_regionabordaje rp ON rp.id = sp.region_id
JOIN organizaciones_subzonaabordajecomunitario sk ON sk.nombre = sp.nombre
JOIN organizaciones_regionabordajecomunitario rk ON rk.id = sk.region_id
WHERE sp.id IN (SELECT subzona_id FROM gestion_organizaciones_datosregionorganizacion)
  AND rk.nombre <> rp.nombre
UNION ALL
--    b) Organización (incluidas las dadas de baja) con otra región cargada.
SELECT
    'region_distinta' AS caso,
    o.id AS organizacion_id,
    rp.nombre AS valor_2745,
    rk.nombre AS valor_2642
FROM gestion_organizaciones_datosregionorganizacion d
JOIN organizaciones_organizacion o ON o.id = d.organizacion_id
JOIN gestion_organizaciones_regionabordaje rp ON rp.id = d.region_id
JOIN organizaciones_regionabordajecomunitario rk ON rk.id = o.region_abordaje_id
WHERE rk.nombre <> rp.nombre
UNION ALL
--    c) Organización (incluidas las dadas de baja) con otra subzona cargada.
SELECT
    'subzona_distinta' AS caso,
    o.id AS organizacion_id,
    sp.nombre AS valor_2745,
    sk.nombre AS valor_2642
FROM gestion_organizaciones_datosregionorganizacion d
JOIN organizaciones_organizacion o ON o.id = d.organizacion_id
JOIN gestion_organizaciones_subzonaabordaje sp ON sp.id = d.subzona_id
JOIN organizaciones_subzonaabordajecomunitario sk ON sk.id = o.subzona_abordaje_id
WHERE sk.nombre <> sp.nombre
ORDER BY caso, organizacion_id;
