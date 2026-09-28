# pylint: disable=invalid-name
"""Issue #2444: carga el rol territorial PNUD en Profile.rol.

Solo modifica ``Profile.rol`` de los usernames listados (origen: CSV del
issue). No crea usuarios, no toca nombre, email, grupos ni contraseñas.
Los usernames que no existen en la base se informan y se omiten.

La reversa no modifica datos: ``rol`` es descriptivo y no otorga permisos.
Para restaurar valores previos, la salida de la migración informa el valor
anterior de cada usuario actualizado.
"""

from django.db import migrations

ROLES_POR_USERNAME = (
    ("rodalaya", "TERRITORIAL PNUD"),
    ("ceciprete", "TERRITORIAL PNUD"),
    ("sofiavirasoro", "TERRITORIAL PNUD"),
    ("vmverbauwede-2", "RESPONSABLE TERRITORIAL PNUD"),
    ("lpswoboda-2", "TERRITORIAL PNUD"),
    ("asalvatico", "TERRITORIAL PNUD"),
    ("jsala", "TERRITORIAL PNUD"),
    ("varubio-2", "TERRITORIAL PNUD"),
    ("cintiarother", "TERRITORIAL PNUD"),
    ("astorres", "RESPONSABLE TERRITORIAL PNUD"),
    ("lilianrojas", "TERRITORIAL PNUD"),
    ("gladysrepetto", "RESPONSABLE TERRITORIAL PNUD"),
    ("cnrebosio-2", "TERRITORIAL PNUD"),
    ("nquelas", "TERRITORIAL PNUD"),
    ("andreapauluk", "TERRITORIAL PNUD"),
    ("ericaparedes", "TERRITORIAL PNUD"),
    ("apachilla", "TERRITORIAL PNUD"),
    ("abmurua", "RESPONSABLE TERRITORIAL PNUD"),
    ("marianogueira", "TERRITORIAL PNUD"),
    ("lucilamoschino", "RESPONSABLE TERRITORIAL PNUD"),
    ("mcmonteavaro-2", "TERRITORIAL PNUD"),
    ("nmoline", "TERRITORIAL PNUD"),
    ("mariamieville", "RESPONSABLE TERRITORIAL PNUD"),
    ("ricamendieta", "TERRITORIAL PNUD"),
    ("fmelis", "TERRITORIAL PNUD"),
    ("jmatorras-2", "RESPONSABLE TERRITORIAL PNUD"),
    ("andreamaidana", "TERRITORIAL PNUD"),
    ("mlinares", "TERRITORIAL PNUD"),
    ("pskusy-2", "TERRITORIAL PNUD"),
    ("silkunz", "TERRITORIAL PNUD"),
    ("cskaleniuk-2", "TERRITORIAL PNUD"),
    ("anaibanez", "RESPONSABLE TERRITORIAL PNUD"),
    ("daniiacono", "TERRITORIAL PNUD"),
    ("fherrera", "TERRITORIAL PNUD"),
    ("gisegrosso", "TERRITORIAL PNUD"),
    ("luisgil", "RESPONSABLE TERRITORIAL PNUD"),
    ("lgarciadiaz", "RESPONSABLE TERRITORIAL PNUD"),
    ("mlgarabello-2", "TERRITORIAL PNUD"),
    ("pfrette-2", "TERRITORIAL PNUD"),
    ("jfranquet", "TERRITORIAL PNUD"),
    ("fahara", "TERRITORIAL PNUD"),
    ("maefernandez", "TERRITORIAL PNUD"),
    ("anffernandez", "TERRITORIAL PNUD"),
    ("elidominguez", "TERRITORIAL PNUD"),
    ("cdelprete", "TERRITORIAL PNUD"),
    ("ddetone", "TERRITORIAL PNUD"),
    ("srcuris-2", "RESPONSABLE TERRITORIAL PNUD"),
    ("juancultrera", "TERRITORIAL PNUD"),
    ("jmcremaschi", "TERRITORIAL PNUD"),
    ("analiacorrea", "TERRITORIAL PNUD"),
    ("ecocorda", "TERRITORIAL PNUD"),
    ("aecejas", "TERRITORIAL PNUD"),
    ("kcarabajal", "TERRITORIAL PNUD"),
    ("maribusleiman", "RESPONSABLE TERRITORIAL PNUD"),
    ("elyburger", "RESPONSABLE TERRITORIAL PNUD"),
    ("monibranchetti", "TERRITORIAL PNUD"),
    ("hecbenegas", "TERRITORIAL PNUD"),
    ("ntaglioli", "TERRITORIAL PNUD"),
    ("nicoavila", "TERRITORIAL PNUD"),
    ("mlarioli-2", "TERRITORIAL PNUD"),
    ("clauarancibia", "RESPONSABLE TERRITORIAL PNUD"),
    ("landrade", "TERRITORIAL PNUD"),
    ("abaltamirano-2", "TERRITORIAL PNUD"),
    ("mlalmiron-2", "TERRITORIAL PNUD"),
    ("galaya", "TERRITORIAL PNUD"),
    ("emilianosimes", "TERRITORIAL PNUD"),
    ("csantana-2", "TERRITORIAL PNUD"),
    ("mariarubio", "RESPONSABLE TERRITORIAL PNUD"),
    ("aaricci", "TERRITORIAL PNUD"),
    ("mplano", "TERRITORIAL PNUD"),
    ("capenedo", "TERRITORIAL PNUD"),
    ("ivnunez", "TERRITORIAL PNUD"),
    ("jnovoa", "TERRITORIAL PNUD"),
    ("paulanegri", "TERRITORIAL PNUD"),
    ("memorales", "TERRITORIAL PNUD"),
    ("cmannino", "TERRITORIAL PNUD"),
    ("marimagallanes", "RESPONSABLE TERRITORIAL PNUD"),
    ("melimachado", "TERRITORIAL PNUD"),
    ("nlorenzo", "TERRITORIAL PNUD"),
    ("hernanjaime", "RESPONSABLE TERRITORIAL PNUD"),
    ("cbherrera-2", "TERRITORIAL PNUD"),
    ("soguffanti", "TERRITORIAL PNUD"),
    ("paogrillo", "TERRITORIAL PNUD"),
    ("mfmendiaz", "TERRITORIAL PNUD"),
    ("xgomez", "TERRITORIAL PNUD"),
    ("raulgiansante", "TERRITORIAL PNUD"),
    ("ggauna", "TERRITORIAL PNUD"),
    ("sferrer-2", "TERRITORIAL PNUD"),
    ("mdfernandez-2", "TERRITORIAL PNUD"),
    ("pirojas", "TERRITORIAL PNUD"),
    ("fdemiryi", "TERRITORIAL PNUD"),
    ("cecichianetta", "TERRITORIAL PNUD"),
    ("jorgecervera", "TERRITORIAL PNUD"),
    ("amcarmona-2", "TERRITORIAL PNUD"),
    ("luiscarllinni", "TERRITORIAL PNUD"),
    ("mcaivano", "TERRITORIAL PNUD"),
    ("msarzamendia-2", "TERRITORIAL PNUD"),
    ("nahuarozarena", "TERRITORIAL PNUD"),
    ("marianzorena", "RESPONSABLE TERRITORIAL PNUD"),
    ("facundoalbornoz", "TERRITORIAL PNUD"),
)


def cargar_roles_territoriales(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    profile_model = apps.get_model("users", "Profile")
    database = schema_editor.connection.alias

    roles = dict(ROLES_POR_USERNAME)
    usuarios = {
        user.username: user
        for user in user_model.objects.using(database).filter(username__in=list(roles))
    }

    actualizados, sin_cambios = [], 0
    for username, rol in ROLES_POR_USERNAME:
        user = usuarios.get(username)
        if user is None:
            continue
        profile, _ = profile_model.objects.using(database).get_or_create(user=user)
        if profile.rol == rol:
            sin_cambios += 1
            continue
        actualizados.append(f"{username}: {profile.rol!r} -> {rol!r}")
        profile.rol = rol
        profile.save(update_fields=["rol"])

    no_encontrados = [u for u, _rol in ROLES_POR_USERNAME if u not in usuarios]
    print(f"\n[#2444] Actualizados: {len(actualizados)}")
    for linea in actualizados:
        print(f"[#2444]   {linea}")
    print(f"[#2444] Sin cambios: {sin_cambios}")
    print(
        f"[#2444] No encontrados ({len(no_encontrados)}): " + ", ".join(no_encontrados)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0055_merge_lease_token_relevador_provincia"),
    ]

    operations = [
        migrations.RunPython(
            cargar_roles_territoriales,
            migrations.RunPython.noop,
            atomic=True,
        ),
    ]
