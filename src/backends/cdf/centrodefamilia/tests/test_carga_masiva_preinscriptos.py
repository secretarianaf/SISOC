"""Criterios de aceptación de la carga masiva de preinscriptos (issue #2939)."""

from datetime import date, timedelta
from io import BytesIO, StringIO
from types import ModuleType
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from centrodefamilia.forms import BeneficiarioForm, ResponsableForm
from centrodefamilia.models import (
    Actividad,
    Beneficiario,
    BeneficiarioResponsable,
    BeneficiariosResponsablesRenaper,
    CargaMasivaPreinscriptos,
    Categoria,
    EdicionCargaMasivaPreinscriptos,
    FilaCargaMasivaPreinscriptos,
    Responsable,
)
from centrodefamilia.services.carga_masiva import lotes
from centrodefamilia.services.carga_masiva.columnas import (
    COLUMNAS,
    ENCABEZADOS,
    HOJA_DATOS,
    MAX_FILAS,
    MAX_TAMANIO_BYTES,
)
from centrodefamilia.services.carga_masiva.excel import (
    generar_comprobante,
    generar_listado_errores,
    generar_plantilla,
    leer_archivo,
)
from centrodefamilia.services.carga_masiva.validacion import cuil_valido
from config.urls_dev import dev_urlpatterns
from core.models import Localidad, Municipio, Provincia

Estado = FilaCargaMasivaPreinscriptos.Estado

DNI_PREINSCRIPTO = 45111222
DNI_TITULAR = 30111222


def _cuil(prefijo, dni):
    base = f"{prefijo}{dni:08d}"
    for verificador in range(10):
        if cuil_valido(f"{base}{verificador}"):
            return int(f"{base}{verificador}")
    raise AssertionError("No se pudo armar un CUIL válido")


CUIL_PREINSCRIPTO = _cuil(20, DNI_PREINSCRIPTO)
CUIL_TITULAR = _cuil(27, DNI_TITULAR)


def _fila(**cambios):
    datos = {
        "cuil": str(CUIL_PREINSCRIPTO),
        "dni": str(DNI_PREINSCRIPTO),
        "apellido": "Pérez",
        "nombre": "Juan",
        "genero": "M",
        "fecha_nacimiento": "01/02/2015",
        "domicilio": "Calle 1 123",
        "provincia": "Buenos Aires",
        "calle": "Calle 1",
        "altura": "123",
        "maximo_nivel_educativo": "Primario incompleto",
        "actividad_preferida": "Deportiva; Educativa",
        "titular_cuil": str(CUIL_TITULAR),
        "titular_dni": str(DNI_TITULAR),
        "titular_apellido": "Gómez",
        "titular_nombre": "Ana",
        "titular_genero": "F",
        "titular_fecha_nacimiento": "10/03/1985",
        "vinculo_parental": "Padre/Madre",
        "titular_calle": "Calle 1",
        "titular_provincia": "Buenos Aires",
        "titular_numero_celular": "1155554444",
    }
    datos.update(cambios)
    return datos


def _otro_preinscripto(dni, **cambios):
    return _fila(cuil=str(_cuil(20, dni)), dni=str(dni), **cambios)


def _archivo(filas, nombre="carga.xlsx"):
    libro = load_workbook(BytesIO(generar_plantilla()))
    hoja = libro[HOJA_DATOS]
    for numero, datos in enumerate(filas, start=2):
        for indice, columna in enumerate(COLUMNAS, start=1):
            hoja.cell(row=numero, column=indice, value=datos.get(columna.clave))
    salida = BytesIO()
    libro.save(salida)
    return SimpleUploadedFile(nombre, salida.getvalue())


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def provincia(db):
    return Provincia.objects.create(nombre="Buenos Aires")


@pytest.fixture
def padron(db):
    """Padrón externo simulado: {cuil: [registros]} (la tabla no la maneja Django)."""
    registros = {}

    def agregar(cuil, dni, genero):
        registros.setdefault(str(cuil), []).append(
            {
                "cuil": str(cuil),
                "dni": str(dni),
                "genero": genero,
                "provincia_tabla": "Buenos Aires",
                "municipio_tabla": "La Plata",
            }
        )

    agregar(CUIL_PREINSCRIPTO, DNI_PREINSCRIPTO, "M")
    with patch(
        "centrodefamilia.services.carga_masiva.validacion.buscar_en_padron",
        side_effect=lambda cuils: {
            str(c): registros[str(c)] for c in cuils if str(c) in registros
        },
    ):
        yield agregar


def _rol_carga_masiva():
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_cdf_carga_masiva",
        defaults={"name": "Cdf Carga Masiva"},
    )
    return permiso


def _usuario_cdf(username, *, carga_masiva):
    user = User.objects.create_user(username=username, password="x")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="centrodefamilia", codename="view_centro"
        )
    )
    if carga_masiva:
        user.user_permissions.add(_rol_carga_masiva())
    return User.objects.get(pk=user.pk)


@pytest.fixture
def usuario(db):
    return _usuario_cdf("cdf-carga", carga_masiva=True)


@pytest.fixture
def renaper(db):
    """RENAPER simulado: {dni: (apellido, nombre, fecha ISO) o el tipo de error}.

    Un DNI que no está en el diccionario responde como el preinscripto de `_fila`.
    """
    personas = {
        DNI_PREINSCRIPTO: ("Pérez", "Juan", "2015-02-01"),
        DNI_TITULAR: ("GÓMEZ", "ana", "1985-03-10"),
    }

    def consultar(dni, sexo):  # pylint: disable=unused-argument
        datos = personas.get(int(dni), ("Pérez", "Juan", "2015-02-01"))
        if isinstance(datos, str):
            return {"success": False, "error": "x", "error_type": datos}
        apellido, nombre, fecha = datos
        return {
            "success": True,
            "data": {"apellido": apellido, "nombre": nombre, "fecha_nacimiento": fecha},
            "datos_api": {
                "apellido": apellido,
                "nombres": nombre,
                "fechaNacimiento": fecha,
            },
        }

    with patch(
        "centrodefamilia.services.carga_masiva.renaper.consultar_datos_renaper",
        side_effect=consultar,
    ) as simulado:
        personas["simulado"] = simulado
        yield personas


def _verificar_todo(carga):
    """Corre las tandas de RENAPER hasta que no quede nadie pendiente."""
    while lotes.verificar_renaper(carga.pk)["consultadas"]:
        pass
    carga.refresh_from_db()
    return carga


@pytest.fixture
def subir(provincia, padron, usuario, renaper):
    def _subir(*filas):
        return _verificar_todo(lotes.crear_carga(_archivo(filas), usuario))

    return _subir


def _filas(carga):
    return {fila.numero_fila: fila for fila in carga.filas.all()}


def _mensajes(fila):
    return " ".join(m["mensaje"] for m in fila.errores + fila.advertencias)


def _crear_titular(**cambios):
    datos = {
        "cuil": CUIL_TITULAR,
        "dni": DNI_TITULAR,
        "apellido": "Gómez",
        "nombre": "Ana",
        "genero": "F",
        "fecha_nacimiento": date(1985, 3, 10),
        "vinculo_parental": "Tutor/Tutora",
        "calle": "Calle 1",
        "provincia": Provincia.objects.get(nombre="Buenos Aires"),
        "numero_celular": "1155554444",
    }
    datos.update(cambios)
    return Responsable.objects.create(**datos)


def _crear_preinscripto(titular, **cambios):
    datos = {
        "cuil": CUIL_PREINSCRIPTO,
        "dni": DNI_PREINSCRIPTO,
        "apellido": "Viejo",
        "nombre": "Apellido",
        "genero": "M",
        "fecha_nacimiento": date(2015, 2, 1),
        "domicilio": "Otro 1",
        "calle": "Otro",
        "maximo_nivel_educativo": "Sin instrucción",
        "responsable": titular,
    }
    datos.update(cambios)
    return Beneficiario.objects.create(**datos)


# ——— Archivo (RN-10, RN-11, RN-16) ———


@pytest.mark.django_db
def test_plantilla_tiene_encabezados_oficiales_y_hojas(provincia):
    libro = load_workbook(BytesIO(generar_plantilla()))

    assert libro.sheetnames[:2] == [HOJA_DATOS, "Instrucciones"]
    assert "Actividades" in libro.sheetnames
    encabezado = [celda.value for celda in libro[HOJA_DATOS][1]]
    assert tuple(encabezado) == ENCABEZADOS
    assert libro[HOJA_DATOS]["A2"].number_format == "@"


@pytest.mark.django_db
def test_ca01_csv_se_rechaza_sin_crear_lote(provincia, usuario):
    archivo = SimpleUploadedFile("carga.csv", b"CUIL preinscripto\n1")

    with pytest.raises(ValidationError, match=".xlsx"):
        lotes.crear_carga(archivo, usuario)

    assert not CargaMasivaPreinscriptos.objects.exists()


@pytest.mark.django_db
def test_ca01_encabezados_distintos_se_rechazan_sin_crear_lote(usuario):
    libro = Workbook()
    hoja = libro.active
    hoja.title = HOJA_DATOS
    hoja.append(list(reversed(ENCABEZADOS)))
    hoja.append(["x"] * len(ENCABEZADOS))
    salida = BytesIO()
    libro.save(salida)

    with pytest.raises(ValidationError, match="encabezados"):
        lotes.crear_carga(SimpleUploadedFile("carga.xlsx", salida.getvalue()), usuario)

    assert not CargaMasivaPreinscriptos.objects.exists()


@pytest.mark.django_db
def test_ca02_tope_de_filas(provincia):
    assert len(leer_archivo(_archivo([_fila()] * MAX_FILAS))) == MAX_FILAS

    with pytest.raises(ValidationError, match="más de 500 filas"):
        leer_archivo(_archivo([_fila()] * (MAX_FILAS + 1)))


@pytest.mark.django_db
def test_archivo_de_mas_de_10_mb_se_rechaza(provincia):
    archivo = _archivo([_fila()])
    archivo.size = MAX_TAMANIO_BYTES + 1

    with pytest.raises(ValidationError, match="10 MB"):
        leer_archivo(archivo)


@pytest.mark.django_db
def test_filas_vacias_se_ignoran_y_dni_numerico_se_recupera(provincia):
    filas = leer_archivo(
        _archivo(
            [_fila(dni=DNI_PREINSCRIPTO, cuil=float(CUIL_PREINSCRIPTO)), {}, _fila()]
        )
    )

    assert [numero for numero, _ in filas] == [2, 4]
    assert filas[0][1]["dni"] == str(DNI_PREINSCRIPTO)
    assert filas[0][1]["cuil"] == str(CUIL_PREINSCRIPTO)


# ——— Validación (sección 7) ———


@pytest.mark.django_db
def test_ca03_archivo_valido_crea_lote_pendiente_sin_cargar_personas(subir):
    carga = subir(_fila())

    assert carga.estado == CargaMasivaPreinscriptos.Estado.PENDIENTE
    assert carga.total_filas == 1
    assert carga.total_validas == 1
    assert not Beneficiario.all_objects.exists()
    assert not Responsable.all_objects.exists()


@pytest.mark.django_db
def test_ca04_cuil_fuera_del_padron(subir):
    carga = subir(_otro_preinscripto(41222333))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert "padrón" in _mensajes(fila)


@pytest.mark.django_db
def test_ca05_dni_distinto_del_cuil_y_digito_verificador(subir):
    cuil_invalido = str(CUIL_PREINSCRIPTO)[:-1] + str(
        (int(str(CUIL_PREINSCRIPTO)[-1]) + 1) % 10
    )
    carga = subir(_fila(dni="45111223"), _fila(cuil=cuil_invalido))

    filas = _filas(carga)
    assert "No coincide con el número de documento del CUIL" in _mensajes(filas[2])
    assert "dígito verificador" in _mensajes(filas[3])
    assert carga.total_errores == 2


@pytest.mark.django_db
def test_dni_y_sexo_invalidos_informan_un_solo_motivo_cada_uno(subir):
    dni_distinto = _filas(subir(_fila(dni="45111223")))[2]
    ambos_invalidos = _filas(subir(_fila(dni="abc", genero="Z")))[2]

    assert [m["columna"] for m in dni_distinto.errores] == ["DNI preinscripto"]
    assert {m["columna"] for m in ambos_invalidos.errores} == {
        "DNI preinscripto",
        "Sexo preinscripto",
    }
    assert "padrón" not in _mensajes(ambos_invalidos)


@pytest.mark.django_db
def test_titular_no_puede_tener_el_mismo_dni_que_el_preinscripto(subir):
    carga = subir(
        _fila(
            titular_cuil=str(CUIL_PREINSCRIPTO),
            titular_dni=str(DNI_PREINSCRIPTO),
            titular_genero="M",
        )
    )

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert "mismo DNI o CUIL que el preinscripto" in _mensajes(fila)
    assert "DNI titular" in {m["columna"] for m in fila.errores}


@pytest.mark.django_db
def test_eliminar_lote_pendiente_borra_filas_ediciones_y_archivo(
    client, subir, usuario, django_capture_on_commit_callbacks
):
    carga = subir(_fila(dni="45111223"))
    lotes.editar_fila(carga.pk, carga.filas.get().pk, {"apellido": "Otro"}, usuario)
    storage, nombre = carga.archivo.storage, carga.archivo.name
    assert storage.exists(nombre)
    client.force_login(usuario)

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = client.post(
            reverse("carga_masiva_eliminar", args=[carga.pk]), follow=True
        )

    assert "Se eliminó el lote" in respuesta.content.decode()
    assert not CargaMasivaPreinscriptos.objects.exists()
    assert not FilaCargaMasivaPreinscriptos.objects.exists()
    assert not EdicionCargaMasivaPreinscriptos.objects.exists()
    assert not storage.exists(nombre)


@pytest.mark.django_db
def test_lote_confirmado_no_se_puede_eliminar(client, subir, usuario):
    carga = subir(_fila())
    lotes.confirmar_carga(carga.pk, usuario)
    client.force_login(usuario)

    respuesta = client.post(
        reverse("carga_masiva_eliminar", args=[carga.pk]), follow=True
    )

    assert "No se puede eliminar un lote confirmado" in respuesta.content.decode()
    assert CargaMasivaPreinscriptos.objects.filter(pk=carga.pk).exists()
    assert Beneficiario.objects.count() == 1


@pytest.mark.django_db
def test_ca06_sexo_distinto_del_padron(subir):
    carga = subir(_fila(genero="F"))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert "sexo no coincide con el del padrón" in _mensajes(fila)


@pytest.mark.django_db
def test_ca07_preinscripto_repetido(subir):
    carga = subir(_fila(), _fila())

    filas = _filas(carga)
    assert filas[2].estado == Estado.VALIDA
    assert filas[3].estado == Estado.ERROR
    assert "ya aparece en la fila 2" in _mensajes(filas[3])


@pytest.mark.django_db
def test_ca08_preinscripto_activo_es_error(subir):
    _crear_preinscripto(_crear_titular())

    carga = subir(_fila())

    assert "ya se encuentra en el programa" in _mensajes(_filas(carga)[2])


@pytest.mark.django_db
def test_ca08_preinscripto_de_baja_se_reactiva_con_datos_del_excel(subir, usuario):
    existente = _crear_preinscripto(_crear_titular())
    existente.delete()

    carga = subir(_fila())
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ADVERTENCIA
    assert "se reactivará" in _mensajes(fila)

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    existente.refresh_from_db()
    assert not existente.is_deleted
    assert existente.apellido == "Pérez"
    assert existente.carga_masiva_origen_id == carga.pk
    assert Beneficiario.objects.count() == 1


@pytest.mark.django_db
def test_ca09_titular_repetido_usa_datos_de_la_primera_fila(subir, padron, usuario):
    padron(_cuil(20, 46111222), 46111222, "M")
    carga = subir(
        _fila(),
        _otro_preinscripto(46111222, titular_numero_celular="1166667777"),
    )

    filas = _filas(carga)
    assert filas[2].estado == Estado.VALIDA
    assert filas[3].estado == Estado.ADVERTENCIA
    assert "titular de la fila 2" in _mensajes(filas[3])

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    titular = Responsable.objects.get()
    assert titular.numero_celular == "1155554444"
    assert titular.creado_por == usuario
    assert titular.beneficiarios.count() == 2


@pytest.mark.django_db
def test_ca10_titular_con_vinculos_distintos(subir, padron, usuario):
    padron(_cuil(20, 46111222), 46111222, "M")
    carga = subir(
        _fila(),
        _otro_preinscripto(46111222, vinculo_parental="Tutor/Tutora"),
    )
    assert carga.total_validas == 2

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    vinculos = dict(
        BeneficiarioResponsable.objects.values_list(
            "beneficiario__dni", "vinculo_parental"
        )
    )
    assert vinculos == {DNI_PREINSCRIPTO: "Padre/Madre", 46111222: "Tutor/Tutora"}


@pytest.mark.django_db
def test_titular_existente_se_actualiza_con_todos_los_datos_del_excel(subir, usuario):
    creador = User.objects.create_user(username="otro")
    titular = _crear_titular(apellido="Otro", nombre="Ana María", creado_por=creador)

    carga = subir(_fila(titular_calle="Nueva 500", titular_numero_celular=""))
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ADVERTENCIA
    assert "Apellido titular" in _mensajes(fila)
    assert "Calle titular" in _mensajes(fila)
    assert lotes.resumen_confirmacion(carga)["titulares_actualizar"] == 1

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    titular.refresh_from_db()
    assert (titular.apellido, titular.nombre) == ("Gómez", "Ana")
    assert titular.calle == "Nueva 500"
    assert titular.numero_celular is None
    assert titular.vinculo_parental == "Tutor/Tutora"
    assert titular.creado_por == creador


@pytest.mark.django_db
def test_titular_de_baja_se_reactiva(subir, usuario):
    titular = _crear_titular()
    titular.delete()

    carga = subir(_fila())
    assert "titular estaba dado de baja" in _mensajes(_filas(carga)[2])

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    titular.refresh_from_db()
    assert not titular.is_deleted


@pytest.mark.django_db
def test_dni_y_cuil_de_titulares_distintos_es_error(subir):
    _crear_titular()
    _crear_titular(cuil=_cuil(20, 31222333), dni=31222333)

    carga = subir(_fila(titular_cuil=str(_cuil(20, 31222333))))

    assert "personas distintas" in _mensajes(_filas(carga)[2])


@pytest.mark.django_db
def test_ca12_municipio_inexistente_es_advertencia_y_se_carga_sin_municipio(
    subir, provincia, usuario
):
    otra = Provincia.objects.create(nombre="Córdoba")
    Municipio.objects.create(nombre="Río Cuarto", provincia=otra)

    carga = subir(_fila(municipio="Río Cuarto"))
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ADVERTENCIA
    assert fila.advertencias[0]["columna"] == "Municipio"

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    beneficiario = Beneficiario.objects.get()
    assert beneficiario.provincia == provincia
    assert beneficiario.municipio is None


@pytest.mark.django_db
def test_catalogos_sin_tildes_ni_mayusculas(subir, provincia, usuario):
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    categoria = Categoria.objects.create(nombre="Deportes")
    actividad = Actividad.objects.create(nombre="Fútbol", categoria=categoria)

    carga = subir(
        _fila(
            provincia="BUENOS  AIRES",
            municipio="la plata",
            actividades_extracurriculares="si",
            actividades_detalle="futbol",
            actividad_preferida="cultural/artistica",
        )
    )
    assert carga.total_validas == 1

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    beneficiario = Beneficiario.objects.get()
    assert beneficiario.municipio == municipio
    assert list(beneficiario.actividades_detalle.all()) == [actividad]
    assert beneficiario.actividad_preferida == ["Cultural/Artística"]


@pytest.mark.django_db
def test_actividades_extracurriculares_obligatorias_si_realiza(subir):
    carga = subir(_fila(actividades_extracurriculares="Sí"))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert fila.errores[0]["columna"] == "Actividades extracurriculares"


@pytest.mark.django_db
def test_nivel_actual_sin_estudiar_es_advertencia_y_no_se_guarda(subir, usuario):
    carga = subir(_fila(nivel_educativo_actual="Primario"))
    assert _filas(carga)[2].estado == Estado.ADVERTENCIA

    lotes.confirmar_carga(carga.pk, usuario)
    assert Beneficiario.objects.get().nivel_educativo_actual is None


@pytest.mark.django_db
def test_una_fila_informa_todos_sus_errores(subir):
    carga = subir(
        _fila(apellido="", fecha_nacimiento="31/02/2015", provincia="Atlántida")
    )

    columnas = {m["columna"] for m in _filas(carga)[2].errores}
    assert {
        "Apellido preinscripto",
        "Fecha de nacimiento preinscripto",
        "Provincia",
    } <= columnas


@pytest.mark.django_db
def test_dato_opcional_mal_cargado_se_carga_sin_el_dato_con_aviso(subir, usuario):
    carga = subir(_fila(correo_electronico="x@", altura="12b", calle=""))
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ADVERTENCIA
    columnas = {m["columna"] for m in fila.advertencias}
    assert {"Correo electrónico", "Altura"} <= columnas

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    beneficiario = Beneficiario.objects.get()
    assert beneficiario.correo_electronico is None
    assert beneficiario.altura is None
    assert beneficiario.calle == ""
    hoja = load_workbook(BytesIO(generar_comprobante(carga))).active
    assert "Correo electrónico" in next(hoja.iter_rows(min_row=2, values_only=True))[8]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "anios,valida",
    [(5, False), (6, True), (17, True), (18, False)],
)
def test_preinscripto_debe_tener_entre_6_y_17_anios(subir, renaper, anios, valida):
    hoy = date.today()
    nacimiento = hoy.replace(year=hoy.year - anios)
    renaper[DNI_PREINSCRIPTO] = ("Pérez", "Juan", nacimiento.isoformat())
    carga = subir(_fila(fecha_nacimiento=nacimiento.strftime("%d/%m/%Y")))

    fila = _filas(carga)[2]
    assert (fila.estado != Estado.ERROR) is valida
    if not valida:
        assert "entre 6 y 17 años" in _mensajes(fila)


@pytest.mark.django_db
def test_titular_no_puede_tener_la_misma_fecha_de_nacimiento(subir):
    carga = subir(_fila(titular_fecha_nacimiento="01/02/2015"))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert "Fecha de nacimiento titular" in {m["columna"] for m in fila.errores}


@pytest.mark.django_db
def test_ca13_provincia_inexistente_es_error(subir):
    carga = subir(_fila(provincia="Atlántida"))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert fila.errores[0]["columna"] == "Provincia"


# ——— Edición, confirmación y comprobante (secciones 5, 8 y 9) ———


@pytest.mark.django_db
def test_se_cargan_las_validas_y_se_rechazan_las_filas_con_error(subir, usuario):
    carga = subir(_fila(), _otro_preinscripto(41222333))
    assert lotes.resumen_confirmacion(carga)["rechazadas"] == 1

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    carga.refresh_from_db()
    assert carga.esta_confirmado
    assert Beneficiario.objects.get().dni == DNI_PREINSCRIPTO
    hoja = load_workbook(BytesIO(generar_comprobante(carga))).active
    filas = {fila[0]: fila for fila in hoja.iter_rows(min_row=2, values_only=True)}
    assert filas[2][5] == "Creado"
    assert filas[3][5] == "Rechazada"
    assert "padrón" in filas[3][7]


@pytest.mark.django_db
def test_sin_filas_validas_no_se_confirma(subir, usuario):
    carga = subir(_otro_preinscripto(41222333))

    assert lotes.confirmar_carga(carga.pk, usuario) is False
    carga.refresh_from_db()
    assert carga.esta_pendiente
    assert not Beneficiario.objects.exists()


@pytest.mark.django_db
def test_ca15_editar_celda_revalida_y_registra(subir, usuario):
    carga = subir(_fila(dni="45111223"))
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR

    cambios = lotes.editar_fila(
        carga.pk, fila.pk, {"dni": str(DNI_PREINSCRIPTO), "no_existe": "x"}, usuario
    )

    assert cambios == 1
    fila.refresh_from_db()
    assert fila.estado == Estado.VALIDA
    edicion = EdicionCargaMasivaPreinscriptos.objects.get()
    assert (edicion.usuario, edicion.columna) == (usuario, "DNI preinscripto")
    assert (edicion.valor_anterior, edicion.valor_nuevo) == (
        "45111223",
        str(DNI_PREINSCRIPTO),
    )


@pytest.mark.django_db
def test_editar_revalida_filas_dependientes(subir, usuario):
    carga = subir(_fila(), _fila())
    primera = _filas(carga)[2]

    lotes.quitar_fila(carga.pk, primera.pk, usuario)

    assert _filas(carga)[3].estado == Estado.VALIDA


@pytest.mark.django_db
def test_ca16_quitar_fila_con_error_habilita_confirmar(subir, usuario):
    carga = subir(_fila(), _otro_preinscripto(41222333))
    con_error = _filas(carga)[3]

    lotes.quitar_fila(carga.pk, con_error.pk, usuario)

    carga.refresh_from_db()
    assert (carga.total_filas, carga.total_errores) == (1, 0)
    assert EdicionCargaMasivaPreinscriptos.objects.get().valor_nuevo == "fila quitada"
    assert lotes.confirmar_carga(carga.pk, usuario) is True
    hoja = load_workbook(BytesIO(generar_comprobante(carga))).active
    assert [fila[0] for fila in hoja.iter_rows(min_row=2, values_only=True)] == [2]


@pytest.mark.django_db
def test_ca17_carga_por_formulario_entre_subida_y_confirmacion(subir, usuario):
    carga = subir(_fila())
    _crear_preinscripto(_crear_titular())

    assert lotes.confirmar_carga(carga.pk, usuario) is False
    assert _filas(carga)[2].estado == Estado.ERROR
    assert Beneficiario.objects.count() == 1


@pytest.mark.django_db
def test_ca18_falla_a_mitad_no_deja_registros(subir, padron, usuario):
    padron(_cuil(20, 46111222), 46111222, "M")
    carga = subir(_fila(), _otro_preinscripto(46111222))
    original = lotes._guardar_preinscripto
    llamadas = []

    def falla_en_la_segunda(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("falla simulada")
        return original(*args, **kwargs)

    with patch.object(lotes, "_guardar_preinscripto", falla_en_la_segunda):
        with pytest.raises(RuntimeError):
            lotes.confirmar_carga(carga.pk, usuario)

    carga.refresh_from_db()
    assert carga.esta_pendiente
    assert not Beneficiario.all_objects.exists()
    assert not Responsable.all_objects.exists()


@pytest.mark.django_db
def test_ca19_lote_confirmado_no_se_confirma_otra_vez(subir, usuario):
    carga = subir(_fila())
    assert lotes.confirmar_carga(carga.pk, usuario) is True

    with pytest.raises(lotes.CargaNoPendiente):
        lotes.confirmar_carga(carga.pk, usuario)
    with pytest.raises(lotes.CargaNoPendiente):
        lotes.editar_fila(carga.pk, carga.filas.get().pk, {"apellido": "X"}, usuario)

    assert Beneficiario.objects.count() == 1


@pytest.mark.django_db
def test_ca20_comprobante_y_descargas_neutralizan_formulas(subir, usuario):
    carga = subir(_fila(), _otro_preinscripto(41222333))
    lotes.editar_fila(
        carga.pk, _filas(carga)[3].pk, {"apellido": "=HYPERLINK(1)"}, usuario
    )

    errores = load_workbook(BytesIO(generar_listado_errores(carga))).active
    filas_error = list(errores.iter_rows(min_row=2, values_only=True))
    assert len(filas_error) == 1
    assert "'=HYPERLINK(1)" in filas_error[0]

    lotes.quitar_fila(carga.pk, _filas(carga)[3].pk, usuario)
    lotes.confirmar_carga(carga.pk, usuario)
    comprobante = load_workbook(BytesIO(generar_comprobante(carga))).active
    fila = next(comprobante.iter_rows(min_row=2, values_only=True))
    beneficiario = Beneficiario.objects.get()
    assert fila[0] == 2
    assert fila[5:7] == ("Creado", "Creado")
    assert fila[9] == beneficiario.pk
    assert beneficiario.carga_masiva_origen == carga
    assert beneficiario.creado_por == usuario
    assert beneficiario.provincia_tabla == "Buenos Aires"


# ——— Pantallas y permisos ———


@pytest.mark.django_db
def test_ca21_sin_permiso_no_accede_a_ninguna_pantalla(client, subir):
    carga = subir(_fila())
    fila = carga.filas.get()
    sin_permiso = _usuario_cdf("sin-rol", carga_masiva=False)
    client.force_login(sin_permiso)
    urls = [
        reverse("carga_masiva_list"),
        reverse("carga_masiva_plantilla"),
        reverse("carga_masiva_detail", args=[carga.pk]),
        reverse("carga_masiva_errores", args=[carga.pk]),
        reverse("carga_masiva_comprobante", args=[carga.pk]),
        reverse("carga_masiva_archivo", args=[carga.pk]),
        reverse("carga_masiva_ediciones", args=[carga.pk]),
        reverse("carga_masiva_fila_editar", args=[carga.pk, fila.pk]),
    ]
    for url in urls:
        assert client.get(url).status_code == 403, url
    for url in (
        reverse("carga_masiva_subir"),
        reverse("carga_masiva_confirmar", args=[carga.pk]),
        reverse("carga_masiva_eliminar", args=[carga.pk]),
        reverse("carga_masiva_deshacer", args=[carga.pk]),
        reverse("carga_masiva_fila_quitar", args=[carga.pk, fila.pk]),
    ):
        assert client.post(url).status_code == 403, url
    listado = client.get(reverse("beneficiarios_list"))
    assert listado.context["additional_buttons"] == []

    carga.refresh_from_db()
    assert carga.esta_pendiente


@pytest.mark.django_db
def test_flujo_completo_por_pantallas(client, provincia, padron, usuario, renaper):
    client.force_login(usuario)

    assert client.get(reverse("carga_masiva_list")).status_code == 200
    plantilla = client.get(reverse("carga_masiva_plantilla"))
    assert plantilla.status_code == 200
    assert "spreadsheetml" in plantilla["Content-Type"]

    respuesta = client.post(
        reverse("carga_masiva_subir"), {"archivo": _archivo([_fila(dni="45111223")])}
    )
    carga = CargaMasivaPreinscriptos.objects.get()
    assert respuesta.url == reverse("carga_masiva_detail", args=[carga.pk])
    detalle = client.get(respuesta.url)
    assert detalle.status_code == 200
    assert detalle.context["puede_confirmar"] is False

    fila = carga.filas.get()
    url_editar = reverse("carga_masiva_fila_editar", args=[carga.pk, fila.pk])
    assert client.get(url_editar).status_code == 200
    client.post(url_editar, {"dni": str(DNI_PREINSCRIPTO)})
    pendiente = client.get(respuesta.url)
    assert pendiente.context["puede_confirmar"] is False
    assert "Verificando con RENAPER" in pendiente.content.decode()
    url_renaper = reverse("carga_masiva_renaper", args=[carga.pk])
    while client.post(url_renaper).json()["pendientes"]:
        pass
    assert client.get(respuesta.url).context["puede_confirmar"] is True
    assert (
        client.get(reverse("carga_masiva_ediciones", args=[carga.pk])).status_code
        == 200
    )
    assert (
        client.get(reverse("carga_masiva_archivo", args=[carga.pk])).status_code == 200
    )

    client.post(reverse("carga_masiva_confirmar", args=[carga.pk]))
    carga.refresh_from_db()
    assert not carga.esta_pendiente
    assert Beneficiario.objects.count() == 1
    comprobante = client.get(reverse("carga_masiva_comprobante", args=[carga.pk]))
    assert comprobante.status_code == 200

    segunda = client.post(
        reverse("carga_masiva_confirmar", args=[carga.pk]), follow=True
    )
    assert "ya fue confirmado" in segunda.content.decode()
    assert Beneficiario.objects.count() == 1


@pytest.mark.django_db
def test_pantallas_de_errores_quitar_y_lote_confirmado(client, subir, usuario):
    carga = subir(_fila(), _otro_preinscripto(41222333))
    con_error = _filas(carga)[3]
    client.force_login(usuario)
    detalle = reverse("carga_masiva_detail", args=[carga.pk])

    assert client.get(detalle, {"estado": "error"}).context["filas"][0] == con_error
    errores = client.get(reverse("carga_masiva_errores", args=[carga.pk]))
    assert errores.status_code == 200
    client.post(reverse("carga_masiva_fila_quitar", args=[carga.pk, con_error.pk]))
    quitadas = client.get(detalle, {"estado": "quitada"}).context["filas"]
    assert list(quitadas) == [con_error]
    assert (
        client.get(
            reverse("carga_masiva_fila_editar", args=[carga.pk, con_error.pk])
        ).url
        == detalle
    )

    client.post(reverse("carga_masiva_confirmar", args=[carga.pk]))
    valida = _filas(carga)[2]
    url_editar = reverse("carga_masiva_fila_editar", args=[carga.pk, valida.pk])
    assert client.get(url_editar).url == detalle
    respuesta = client.post(url_editar, {"apellido": "Otro"}, follow=True)
    assert "no admite cambios" in respuesta.content.decode()
    assert client.get(reverse("carga_masiva_list")).context["cargas"][0] == carga


@pytest.mark.django_db
def test_subir_archivo_invalido_por_pantalla_muestra_mensaje(client, usuario):
    client.force_login(usuario)

    respuesta = client.post(
        reverse("carga_masiva_subir"),
        {"archivo": SimpleUploadedFile("datos.csv", b"a,b")},
        follow=True,
    )

    assert "Solo se aceptan archivos .xlsx" in respuesta.content.decode()
    assert not CargaMasivaPreinscriptos.objects.exists()


@pytest.mark.django_db
def test_rf15_listado_de_preinscriptos_tiene_boton_de_carga_masiva(client, usuario):
    client.force_login(usuario)

    respuesta = client.get(reverse("beneficiarios_list"))

    url = reverse("carga_masiva_list")
    assert [b["url"] for b in respuesta.context["additional_buttons"]] == [url]
    assert f'href="{url}"' in respuesta.content.decode()


@pytest.mark.django_db
def test_calle_opcional_en_el_formulario_de_preinscripcion(provincia):
    beneficiario = BeneficiarioForm()
    responsable = ResponsableForm()

    assert beneficiario.fields["calle"].required is False
    assert responsable.fields["calle"].required is False
    assert "observaciones" not in beneficiario.fields


# ——— Deshacer el último lote ———


@pytest.mark.django_db
def test_deshacer_borra_lo_creado_y_restaura_lo_reactivado(subir, padron, usuario):
    padron(_cuil(20, 46111222), 46111222, "M")
    titular = _crear_titular(calle="Vieja")
    dado_de_baja = _crear_preinscripto(
        titular, cuil=_cuil(20, 46111222), dni=46111222, apellido="Antes"
    )
    dado_de_baja.delete()
    carga = subir(
        _fila(titular_calle="Nueva"),
        _otro_preinscripto(46111222, titular_calle="Nueva"),
    )
    assert lotes.confirmar_carga(carga.pk, usuario) is True
    creado = Beneficiario.objects.get(dni=DNI_PREINSCRIPTO)

    lotes.deshacer_carga(carga.pk, usuario)

    carga.refresh_from_db()
    assert carga.estado == CargaMasivaPreinscriptos.Estado.DESHECHO
    assert carga.deshecho_por == usuario
    assert not Beneficiario.all_objects.filter(pk=creado.pk).exists()
    dado_de_baja.refresh_from_db()
    assert dado_de_baja.is_deleted
    assert dado_de_baja.apellido == "Antes"
    assert dado_de_baja.carga_masiva_origen is None
    titular.refresh_from_db()
    assert titular.calle == "Vieja"
    assert not BeneficiarioResponsable.all_objects.filter(
        beneficiario__dni=DNI_PREINSCRIPTO
    ).exists()


@pytest.mark.django_db
def test_deshacer_borra_el_titular_creado_por_el_lote(subir, usuario):
    carga = subir(_fila())
    lotes.confirmar_carga(carga.pk, usuario)

    lotes.deshacer_carga(carga.pk, usuario)

    assert not Beneficiario.all_objects.exists()
    assert not Responsable.all_objects.exists()


@pytest.mark.django_db
def test_no_se_deshace_si_modificaron_un_preinscripto(subir, usuario):
    carga = subir(_fila())
    lotes.confirmar_carga(carga.pk, usuario)
    beneficiario = Beneficiario.objects.get()
    beneficiario.barrio = "Cambiado después"
    beneficiario.save()

    with pytest.raises(lotes.CargaNoDeshacible, match="modificados"):
        lotes.deshacer_carga(carga.pk, usuario)

    assert Beneficiario.objects.filter(pk=beneficiario.pk).exists()


@pytest.mark.django_db
def test_solo_se_deshace_el_ultimo_lote(subir, padron, usuario):
    primera = subir(_fila())
    lotes.confirmar_carga(primera.pk, usuario)
    padron(_cuil(20, 46111222), 46111222, "M")
    segunda = subir(_otro_preinscripto(46111222))
    lotes.confirmar_carga(segunda.pk, usuario)
    primera.refresh_from_db()

    assert "último lote" in lotes.motivo_no_deshacer(primera)
    with pytest.raises(lotes.CargaNoDeshacible):
        lotes.deshacer_carga(primera.pk, usuario)
    lotes.deshacer_carga(segunda.pk, usuario)
    primera.refresh_from_db()
    assert "último lote" in lotes.motivo_no_deshacer(primera)


@pytest.mark.django_db
def test_deshacer_por_pantalla(client, subir, usuario):
    carga = subir(_fila())
    client.force_login(usuario)
    url = reverse("carga_masiva_deshacer", args=[carga.pk])

    pendiente = client.post(url, follow=True)
    assert "Solo se puede deshacer un lote confirmado" in pendiente.content.decode()

    lotes.confirmar_carga(carga.pk, usuario)
    respuesta = client.post(url, follow=True)
    assert "Se deshizo el lote" in respuesta.content.decode()
    assert not Beneficiario.all_objects.exists()
    comprobante = client.get(reverse("carga_masiva_comprobante", args=[carga.pk]))
    assert comprobante.status_code == 200


@pytest.mark.django_db
def test_plantilla_tiene_desplegables_dependientes_de_ubicacion(provincia):
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    Localidad.objects.create(nombre="Tolosa", municipio=municipio)

    libro = load_workbook(BytesIO(generar_plantilla()))

    ubicaciones = libro["Ubicaciones"]
    assert ubicaciones.sheet_state == "hidden"
    assert [c.value for c in ubicaciones[2]] == [
        "Buenos Aires",
        "La Plata",
        "Buenos Aires|La Plata",
        "Tolosa",
    ]
    formulas = {
        str(validacion.sqref): validacion.formula1
        for validacion in libro[HOJA_DATOS].data_validations.dataValidation
    }
    letra = {c.value: c.column_letter for c in libro[HOJA_DATOS][1]}
    municipio_col = formulas[f"{letra['Municipio']}2:{letra['Municipio']}501"]
    localidad_col = formulas[f"{letra['Localidad']}2:{letra['Localidad']}501"]
    assert "OFFSET" in municipio_col and f"${letra['Provincia']}2" in municipio_col
    assert f"${letra['Municipio']}2" in localidad_col
    assert (
        f"{letra['Provincia titular']}2"
        in formulas[f"{letra['Municipio titular']}2:{letra['Municipio titular']}501"]
    )


# ——— RENAPER ———


@pytest.mark.django_db
def test_renaper_rechaza_diferencias_y_muestra_el_dato_de_renaper(
    subir, renaper, usuario
):
    renaper[DNI_PREINSCRIPTO] = ("Pérez Gómez", "Juan", "2015-02-01")
    renaper[DNI_TITULAR] = ("Gómez", "Ana", "1985-03-11")

    carga = subir(_fila())

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    motivos = {m["columna"]: m["mensaje"] for m in fila.errores}
    assert motivos["Apellido preinscripto"] == "No coincide con RENAPER: «Pérez Gómez»."
    assert (
        motivos["Fecha de nacimiento titular"]
        == "No coincide con RENAPER: «11/03/1985»."
    )
    assert "Nombre preinscripto" not in motivos


@pytest.mark.django_db
def test_renaper_sin_tildes_ni_mayusculas_coincide(subir):
    carga = subir(_fila(apellido="PEREZ", titular_apellido="gomez"))

    assert _filas(carga)[2].estado == Estado.VALIDA


@pytest.mark.django_db
def test_renaper_no_encontrado_o_fallecido_es_error(subir, renaper, padron):
    padron(_cuil(20, 46111222), 46111222, "M")
    renaper[DNI_PREINSCRIPTO] = "no_match"
    renaper[46111222] = "fallecido"

    carga = subir(_fila(), _otro_preinscripto(46111222, titular_dni="30111222"))

    filas = _filas(carga)
    assert "No se encontró en RENAPER" in _mensajes(filas[2])
    assert "falleció" in _mensajes(filas[3])


@pytest.mark.django_db
def test_renaper_caido_deja_pendiente_y_bloquea_confirmar(
    provincia, padron, usuario, renaper
):
    renaper[DNI_PREINSCRIPTO] = "timeout"
    carga = lotes.crear_carga(_archivo([_fila()]), usuario)

    avance = lotes.verificar_renaper(carga.pk)

    assert avance == {"consultadas": 2, "fallas": 1, "pendientes": 1}
    with pytest.raises(lotes.VerificacionRenaperPendiente):
        lotes.confirmar_carga(carga.pk, usuario)
    renaper[DNI_PREINSCRIPTO] = ("Pérez", "Juan", "2015-02-01")
    assert lotes.verificar_renaper(carga.pk)["pendientes"] == 0
    assert lotes.confirmar_carga(carga.pk, usuario) is True


@pytest.mark.django_db
def test_renaper_consulta_una_vez_por_persona(subir, renaper, padron):
    padron(_cuil(20, 46111222), 46111222, "M")

    subir(_fila(), _otro_preinscripto(46111222))

    assert renaper["simulado"].call_count == 3


@pytest.mark.django_db
def test_confirmar_guarda_respuesta_renaper_y_borra_las_consultas(subir, usuario):
    carga = subir(_fila())
    assert carga.consultas_renaper.count() == 2

    lotes.confirmar_carga(carga.pk, usuario)

    assert not carga.consultas_renaper.exists()
    guardados = BeneficiariosResponsablesRenaper.objects.order_by("tipo")
    assert [(r.dni, r.tipo, r.apellido) for r in guardados] == [
        (str(DNI_PREINSCRIPTO), "Beneficiario", "Pérez"),
        (str(DNI_TITULAR), "Responsable", "GÓMEZ"),
    ]


@pytest.mark.django_db
def test_renaper_por_pantalla_con_lote_confirmado(client, subir, usuario):
    carga = subir(_fila())
    lotes.confirmar_carga(carga.pk, usuario)
    client.force_login(usuario)

    respuesta = client.post(reverse("carga_masiva_renaper", args=[carga.pk]))

    assert respuesta.status_code == 409


@pytest.mark.django_db
def test_confirmar_con_renaper_pendiente_por_pantalla(
    client, provincia, padron, usuario, renaper
):
    carga = lotes.crear_carga(_archivo([_fila()]), usuario)
    client.force_login(usuario)

    respuesta = client.post(
        reverse("carga_masiva_confirmar", args=[carga.pk]), follow=True
    )

    assert "sin verificar contra RENAPER" in respuesta.content.decode()
    assert not Beneficiario.objects.exists()


# ——— Retención de 90 días ———


@pytest.mark.django_db
def test_lotes_pendientes_vencidos_se_eliminan(
    client, subir, usuario, django_capture_on_commit_callbacks
):
    vencido = subir(_fila())
    reciente = subir(_fila())
    confirmado = subir(_fila())
    lotes.confirmar_carga(confirmado.pk, usuario)
    hace_91_dias = timezone.now() - timedelta(days=91)
    CargaMasivaPreinscriptos.objects.filter(pk__in=[vencido.pk, confirmado.pk]).update(
        fecha_subida=hace_91_dias
    )
    storage, nombre = vencido.archivo.storage, vencido.archivo.name
    client.force_login(usuario)

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = client.get(reverse("carga_masiva_list"))

    assert "se eliminan a los 90 días" in respuesta.content.decode()
    assert set(CargaMasivaPreinscriptos.objects.values_list("pk", flat=True)) == {
        reciente.pk,
        confirmado.pk,
    }
    assert not storage.exists(nombre)


@pytest.mark.django_db
def test_comando_de_purga(subir):
    vencido = subir(_fila())
    CargaMasivaPreinscriptos.objects.filter(pk=vencido.pk).update(
        fecha_subida=timezone.now() - timedelta(days=31)
    )
    salida = StringIO()

    call_command("purgar_cargas_masivas_pendientes", "--dias", "30", stdout=salida)

    assert "Lotes pendientes eliminados: 1." in salida.getvalue()
    assert not CargaMasivaPreinscriptos.objects.exists()


def test_original_se_descarga_por_el_lote_con_cache_privada(client, usuario, subir):
    carga = subir(_fila())
    client.force_login(usuario)
    descarga = client.get(reverse("carga_masiva_archivo", args=[carga.pk]))
    assert descarga.status_code == 200
    assert descarga["Content-Disposition"] == 'attachment; filename="carga.xlsx"'
    with carga.archivo.open("rb") as original:
        assert b"".join(descarga.streaming_content) == original.read()
    assert {"private", "no-store"} <= {
        directive.strip() for directive in descarga["Cache-Control"].split(",")
    }


def test_archivo_del_lote_no_expone_url_de_storage(subir):
    carga = subir(_fila())
    with pytest.raises(NotImplementedError, match="privados"):
        _ = carga.archivo.url


def test_urls_dev_reservan_los_originales_cdf(settings, tmp_path, client):
    settings.DEBUG = True
    settings.RUNNING_TESTS = False
    urlconf = ModuleType("cdf_test_dev_media_urls")
    urlconf.urlpatterns = dev_urlpatterns()
    settings.ROOT_URLCONF = urlconf
    privado = tmp_path / "centrodefamilia" / "cargas_masivas" / "fixture.xlsx"
    privado.parent.mkdir(parents=True)
    privado.write_bytes(b"fixture sintetico")
    (tmp_path / "publico.txt").write_bytes(b"publico")

    assert (
        client.get("/media/centrodefamilia/cargas_masivas/fixture.xlsx").status_code
        == 404
    )
    publico = client.get("/media/publico.txt")
    assert publico.status_code == 200
    assert b"".join(publico.streaming_content) == b"publico"
