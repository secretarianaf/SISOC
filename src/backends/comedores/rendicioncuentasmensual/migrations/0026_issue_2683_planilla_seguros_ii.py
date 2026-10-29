# Actualiza etiquetas sin modificar los códigos ni los archivos existentes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rendicioncuentasmensual", "0025_origen_acta_auditoria"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentacionadjunta",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("formulario_i", "Formulario I - Certificación de Cuenta Bancaria"),
                    ("formulario_ii", "Formulario II - Resumen"),
                    (
                        "formulario_iii",
                        "Formulario III - Desagregado por Facturas Prestación Alimentaria",
                    ),
                    (
                        "formulario_iii_alimentario",
                        "Formulario III - Desagregado por Facturas Prestación Alimentaria",
                    ),
                    (
                        "formulario_iii_siph",
                        "Formulario III - Desagregado por Facturas SIPH",
                    ),
                    ("formulario_iv", "Formulario IV - Recibo de Fondos"),
                    (
                        "formulario_v",
                        "Formulario V - Certificación de Prestaciones Alimentarias",
                    ),
                    (
                        "formulario_v_alimentario",
                        "Formulario V - Certificación de Prestaciones Alimentarias",
                    ),
                    ("formulario_v_siph", "Formulario V - Certificación de SIPH"),
                    ("formulario_vi", "Formulario VI - Planilla de Pagos"),
                    ("extracto_bancario", "Extracto Bancario"),
                    (
                        "comprobantes_alimentario",
                        "Facturas y Tickets Prestación Alimentaria",
                    ),
                    ("comprobantes_siph", "Facturas y Tickets SIPH"),
                    ("planilla_seguros", "Planilla de Seguros II"),
                    ("otros", "Documentación Adicional"),
                ],
                default="comprobantes_alimentario",
                max_length=40,
                verbose_name="Categoría",
            ),
        ),
        migrations.AlterField(
            model_name="solicituddocumentofaltante",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("formulario_i", "Formulario I - Certificación de Cuenta Bancaria"),
                    ("formulario_ii", "Formulario II - Resumen"),
                    (
                        "formulario_iii",
                        "Formulario III - Desagregado por Facturas Prestación Alimentaria",
                    ),
                    (
                        "formulario_iii_alimentario",
                        "Formulario III - Desagregado por Facturas Prestación Alimentaria",
                    ),
                    (
                        "formulario_iii_siph",
                        "Formulario III - Desagregado por Facturas SIPH",
                    ),
                    ("formulario_iv", "Formulario IV - Recibo de Fondos"),
                    (
                        "formulario_v",
                        "Formulario V - Certificación de Prestaciones Alimentarias",
                    ),
                    (
                        "formulario_v_alimentario",
                        "Formulario V - Certificación de Prestaciones Alimentarias",
                    ),
                    ("formulario_v_siph", "Formulario V - Certificación de SIPH"),
                    ("formulario_vi", "Formulario VI - Planilla de Pagos"),
                    ("extracto_bancario", "Extracto Bancario"),
                    (
                        "comprobantes_alimentario",
                        "Facturas y Tickets Prestación Alimentaria",
                    ),
                    ("comprobantes_siph", "Facturas y Tickets SIPH"),
                    ("planilla_seguros", "Planilla de Seguros II"),
                    ("otros", "Documentación Adicional"),
                ],
                max_length=40,
            ),
        ),
    ]
