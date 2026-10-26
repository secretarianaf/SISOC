from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dispositivos", "0006_dispositivo_ubicacion_georef"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dispositivo",
            options={
                "ordering": ["-created_at", "nombre_institucion"],
                "permissions": [
                    ("ver_mapa_dispositivo", "Puede ver el mapa de dispositivos")
                ],
                "verbose_name": "Dispositivo",
                "verbose_name_plural": "Dispositivos",
            },
        ),
    ]
