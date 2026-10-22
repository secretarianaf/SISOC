# pylint: disable=invalid-name
from django.db import migrations, models
import django.db.models.deletion


def recuperar_origen_actas(apps, schema_editor):
    rendicion = apps.get_model("rendicioncuentasmensual", "RendicionCuentaMensual")
    registros = rendicion.objects.using(schema_editor.connection.alias)
    relaciones = rendicion.rendiciones_incluidas.through.objects.using(
        schema_editor.connection.alias
    )
    enlaces = list(
        relaciones.order_by("pk").values_list(
            "from_rendicioncuentamensual_id", "to_rendicioncuentamensual_id"
        )
    )
    vecinos = {}
    for origen, incluida in enlaces:
        vecinos.setdefault(origen, set()).add(incluida)
        vecinos.setdefault(incluida, set()).add(origen)
    actas = dict(
        registros.filter(genera_acta_auditoria=True).values_list("pk", "fecha_auditada")
    )
    pendientes = set(actas)
    while pendientes:
        grupo = set()
        explorar = {min(pendientes)}
        while explorar:
            actual = explorar.pop()
            if actual in grupo:
                continue
            grupo.add(actual)
            explorar.update(vecinos.get(actual, set()) - grupo)
        pendientes.difference_update(grupo)
        if not grupo.issubset(actas) or len({actas[item] for item in grupo}) != 1:
            # Un grupo histórico inconsistente requiere identificar su origen.
            continue
        # Los guardados previos insertaban primero los vínculos de la base y
        # luego los de las incorporadas. No inferir el origen por PK o estado.
        origen = next(
            (base for base, incluida in enlaces if base in grupo and incluida in grupo),
            min(grupo),
        )
        registros.filter(pk__in=grupo).update(rendicion_origen_acta_id=origen)


class Migration(migrations.Migration):
    dependencies = [("rendicioncuentasmensual", "0024_cierre_gestion_auditoria")]

    operations = [
        migrations.AddField(
            model_name="rendicioncuentamensual",
            name="rendicion_origen_acta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rendiciones_del_acta",
                to="rendicioncuentasmensual.rendicioncuentamensual",
                verbose_name="Rendición que originó el acta de auditoría",
            ),
        ),
        migrations.RunPython(recuperar_origen_actas, migrations.RunPython.noop),
    ]
