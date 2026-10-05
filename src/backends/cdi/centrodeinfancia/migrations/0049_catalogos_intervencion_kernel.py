"""Las FKs a catálogos de intervención apuntan a ``catalogo_intervenciones``.

Solo estado: las columnas y FKs físicas no cambian (misma tabla destino).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo_intervenciones", "0001_catalogos_desde_intervenciones"),
        ("centrodeinfancia", "0048_issue_2417_respuestas_no_sabe"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="intervencioncentroinfancia",
                    name="destinatario",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipodestinatario",
                        verbose_name="Destinatario",
                    ),
                ),
                migrations.AlterField(
                    model_name="intervencioncentroinfancia",
                    name="forma_contacto",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipocontacto",
                        verbose_name="Forma de contacto",
                    ),
                ),
                migrations.AlterField(
                    model_name="intervencioncentroinfancia",
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
                    model_name="intervencioncentroinfancia",
                    name="tipo_intervencion",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalogo_intervenciones.tipointervencion",
                        verbose_name="Tipo de intervención",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
