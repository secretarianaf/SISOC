"""Encuesta de satisfacción de CDI: inmutabilidad y vista del área (solo MySQL).

Crea:

- dos triggers que impiden editar o borrar una respuesta registrada (RF-19).
  Solo admiten la anulación lógica (irreversible) y la purga de ``ip_hash``;
- la vista ``v_210SatisfaccionCDI_descarga``, contrato de lectura con el
  procesamiento del área: una fila por respuesta, con código y etiqueta, sin
  ``token``, ``ip_hash``, captcha ni hash de integridad. ``fecha_carga`` sale
  en hora Argentina (UTC-3, sin horario de verano desde 2009).

Requiere que el usuario de la migración tenga los privilegios ``TRIGGER`` y
``CREATE VIEW``; con el binlog activo, MySQL puede pedir además ``SUPER`` o
``log_bin_trust_function_creators = 1``. Es idempotente: si falla, se corrige
el permiso y se vuelve a correr.

Las etiquetas están congeladas acá a propósito: una migración no importa el
código vivo. Si cambia una etiqueta, va en una migración nueva.
En SQLite (tests y desarrollo local) no hace nada; la inmutabilidad la cubre el
modelo.
"""

from django.db import migrations

TABLA = "centrodeinfancia_encuestasatisfaccionrespuesta"
VISTA = "v_210SatisfaccionCDI_descarga"
TRIGGER_UPDATE = "trg_cdi_encuesta_no_update"
TRIGGER_DELETE = "trg_cdi_encuesta_no_delete"

PREGUNTAS = (
    "p01_informacion_avances",
    "p02_recomendaciones_hogar",
    "p03_escucha_respeto",
    "p04_respeto_cultura",
    "p05_comodidad_dudas",
    "p06_ingreso_alegria",
    "p07_deteccion_malestar",
    "p08_seguridad_proteccion",
    "p09_confianza_educadora",
    "p10_participacion_juegos",
    "p11_materiales_adecuados",
    "p12_limpieza_orden",
    "p13_alimentacion",
    "p14_medidas_seguridad",
    "p15_horario_adecuado",
)

# Las columnas que no son anulación, purga de ip_hash ni updated_at.
COLUMNAS_INMUTABLES = (
    "uuid_respuesta",
    "version_instrumento",
    "canal_ingreso",
    "cdi_id",
    "jurisdiccion",
    "departamento",
    "institucion",
    "codigo_institucion",
    "sala",
    "sala_origen",
    "fecha_carga",
    *PREGUNTAS,
    "comentarios",
    "ts_inicio",
    "ts_envio",
    "duracion_seg",
    "token_id",
    "captcha_proveedor",
    "captcha_score",
    "dispositivo_tipo",
    "app_version",
    "hash_integridad",
    "created_at",
)

ETIQUETAS = {
    "canal": {1: "QR", 2: "URL acortada", 9: "Sin identificar"},
    "sala": {
        1: "Menos de un año",
        2: "1 año",
        3: "2 años",
        4: "3 años",
        5: "4 años",
        6: "Multiedad",
    },
    "sala_origen": {
        1: "Salas de la nómina del CDI",
        2: "Lista completa (CDI sin nómina activa)",
    },
    "escala": {
        1: "Nunca",
        2: "Casi nunca",
        3: "A veces",
        4: "Casi siempre",
        5: "Siempre",
        9: "No brinda alimentación",
    },
    "dispositivo": {1: "Móvil", 2: "Tablet", 3: "Escritorio", 9: "Sin identificar"},
    "estado": {1: "Válido", 2: "Anulado por auditoría"},
}


def _case(columna, catalogo):
    ramas = " ".join(
        f"WHEN {codigo} THEN '{etiqueta}'"
        for codigo, etiqueta in ETIQUETAS[catalogo].items()
    )
    return f"CASE r.`{columna}` {ramas} END"


def _sql_trigger_update():
    cambia_contenido = " OR ".join(
        f"NOT (OLD.`{columna}` <=> NEW.`{columna}`)" for columna in COLUMNAS_INMUTABLES
    )
    cambia_anulacion = " OR ".join(
        f"NOT (OLD.`{columna}` <=> NEW.`{columna}`)"
        for columna in ("motivo_anulacion", "anulado_por_id", "fecha_anulacion")
    )
    return f"""
CREATE TRIGGER `{TRIGGER_UPDATE}` BEFORE UPDATE ON `{TABLA}`
FOR EACH ROW
BEGIN
    IF {cambia_contenido} THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Encuesta CDI: el contenido de una respuesta no puede modificarse; use la anulacion logica.';
    END IF;
    IF OLD.`estado_registro` = 2 AND (NEW.`estado_registro` <> 2 OR {cambia_anulacion}) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Encuesta CDI: una anulacion no puede revertirse ni editarse.';
    END IF;
    IF NEW.`ip_hash` IS NOT NULL AND NOT (OLD.`ip_hash` <=> NEW.`ip_hash`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Encuesta CDI: ip_hash solo puede purgarse (NULL).';
    END IF;
END
"""


def _sql_trigger_delete():
    return f"""
CREATE TRIGGER `{TRIGGER_DELETE}` BEFORE DELETE ON `{TABLA}`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
        'Encuesta CDI: las respuestas no se eliminan; use la anulacion logica.';
END
"""


def _sql_vista():
    preguntas = ",\n    ".join(
        f"r.`{campo}`,\n    {_case(campo, 'escala')} AS `{campo}_etiqueta`"
        for campo in PREGUNTAS
    )
    return f"""
CREATE OR REPLACE VIEW `{VISTA}` AS
SELECT
    r.`id` AS `id_respuesta`,
    LEFT(REPLACE(r.`uuid_respuesta`, '-', ''), 8) AS `comprobante`,
    r.`version_instrumento`,
    CONVERT_TZ(r.`fecha_carga`, '+00:00', '-03:00') AS `fecha_carga`,
    r.`canal_ingreso`,
    {_case('canal_ingreso', 'canal')} AS `canal_ingreso_etiqueta`,
    r.`jurisdiccion`,
    r.`departamento`,
    r.`cdi_id`,
    r.`institucion`,
    r.`codigo_institucion`,
    r.`sala`,
    {_case('sala', 'sala')} AS `sala_etiqueta`,
    r.`sala_origen`,
    {_case('sala_origen', 'sala_origen')} AS `sala_origen_etiqueta`,
    {preguntas},
    r.`comentarios`,
    r.`duracion_seg`,
    {_case('dispositivo_tipo', 'dispositivo')} AS `dispositivo`,
    r.`estado_registro`,
    {_case('estado_registro', 'estado')} AS `estado_registro_etiqueta`,
    r.`motivo_anulacion`
FROM `{TABLA}` r
"""


def crear_objetos_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(f"DROP TRIGGER IF EXISTS `{TRIGGER_UPDATE}`")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS `{TRIGGER_DELETE}`")
    schema_editor.execute(_sql_trigger_update())
    schema_editor.execute(_sql_trigger_delete())
    schema_editor.execute(_sql_vista())


def borrar_objetos_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(f"DROP VIEW IF EXISTS `{VISTA}`")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS `{TRIGGER_UPDATE}`")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS `{TRIGGER_DELETE}`")


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0058_encuesta_satisfaccion"),
    ]

    operations = [
        # MySQL no admite DDL dentro de una transacción.
        migrations.RunPython(crear_objetos_mysql, borrar_objetos_mysql, atomic=False),
    ]
