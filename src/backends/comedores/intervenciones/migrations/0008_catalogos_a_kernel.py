"""``intervenciones`` deja de declarar los catálogos (ahora en el kernel).

Solo estado: ``Intervencion`` apunta a ``catalogo_intervenciones`` y las tablas
``intervenciones_*`` las sigue usando el kernel.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0049_catalogos_intervencion_kernel"),
        ("catalogo_intervenciones", "0001_catalogos_desde_intervenciones"),
        ("intervenciones", "0007_intervencion_admision_backfill"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="intervencion",
                    name="subintervencion",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.subintervencion",
                        verbose_name="Sub-tipo de intervención",
                    ),
                ),
                migrations.AlterField(
                    model_name="intervencion",
                    name="forma_contacto",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipocontacto",
                        verbose_name="Forma de contacto",
                    ),
                ),
                migrations.AlterField(
                    model_name="intervencion",
                    name="destinatario",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipodestinatario",
                        verbose_name="Destinatario",
                    ),
                ),
                migrations.AlterField(
                    model_name="intervencion",
                    name="tipo_intervencion",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipointervencion",
                        verbose_name="Tipo de intervención",
                    ),
                ),
                migrations.DeleteModel(
                    name="SubIntervencion",
                ),
                migrations.DeleteModel(
                    name="TipoContacto",
                ),
                migrations.DeleteModel(
                    name="TipoDestinatario",
                ),
                migrations.DeleteModel(
                    name="TipoIntervencion",
                ),
            ],
            database_operations=[],
        ),
    ]
