from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0062_inet_asistencia"),
        ("comedores", "0063_merge_subido_por_responsable_tarjeta"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlcanceProgramaComedor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "programa",
                    models.CharField(
                        choices=[
                            ("pnud", "PNUD"),
                            ("alimentar_comunidad", "Alimentar comunidad"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alcances_programa_comedor",
                        to="users.profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alcance por programa de comedores",
                "verbose_name_plural": "Alcances por programa de comedores",
            },
        ),
        migrations.AddConstraint(
            model_name="alcanceprogramacomedor",
            constraint=models.UniqueConstraint(
                fields=("profile", "programa"),
                name="uniq_alcance_programa_comedor_profile_programa",
            ),
        ),
    ]
