"""Criterios de aceptación de la carga masiva de preinscriptos (issue #2939)."""

from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from centrodefamilia.models import (
    Actividad,
    Beneficiario,
    BeneficiarioResponsable,
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
from core.models import Municipio, Provincia

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
        "observaciones": "Llega en transporte escolar",
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


@pytest.fixture
def usuario(db):
    user = User.objects.create_user(username="cdf-carga", password="x")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="centrodefamilia", codename="view_centro"
        )
    )
    return User.objects.get(pk=user.pk)


@pytest.fixture
def subir(provincia, padron, usuario):
    def _subir(*filas):
        return lotes.crear_carga(_archivo(filas), usuario)

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
def test_ca11_titular_existente_con_apellido_distinto_es_error(subir):
    _crear_titular(apellido="Otro")

    carga = subir(_fila())

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert fila.errores[0]["columna"] == "Apellido titular"


@pytest.mark.django_db
def test_ca11_titular_existente_actualiza_solo_contacto_y_domicilio(subir, usuario):
    creador = User.objects.create_user(username="otro")
    titular = _crear_titular(creado_por=creador)

    carga = subir(_fila(titular_calle="Nueva 500", titular_numero_celular=""))
    fila = _filas(carga)[2]
    assert fila.estado == Estado.ADVERTENCIA
    assert "Se actualizarán los datos de contacto" in _mensajes(fila)
    assert lotes.resumen_confirmacion(carga)["titulares_actualizar"] == 1

    assert lotes.confirmar_carga(carga.pk, usuario) is True
    titular.refresh_from_db()
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
        _fila(apellido="", fecha_nacimiento="31/02/2015", correo_electronico="x@")
    )

    columnas = {m["columna"] for m in _filas(carga)[2].errores}
    assert {
        "Apellido preinscripto",
        "Fecha de nacimiento preinscripto",
        "Correo electrónico",
    } <= columnas


@pytest.mark.django_db
def test_ca13_provincia_inexistente_es_error(subir):
    carga = subir(_fila(provincia="Atlántida"))

    fila = _filas(carga)[2]
    assert fila.estado == Estado.ERROR
    assert fila.errores[0]["columna"] == "Provincia"


# ——— Edición, confirmación y comprobante (secciones 5, 8 y 9) ———


@pytest.mark.django_db
def test_ca14_con_errores_no_se_confirma(subir, usuario):
    carga = subir(_fila(), _otro_preinscripto(41222333))

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
    assert fila[8] == beneficiario.pk
    assert beneficiario.carga_masiva_origen == carga
    assert beneficiario.creado_por == usuario
    assert beneficiario.observaciones == "Llega en transporte escolar"
    assert beneficiario.provincia_tabla == "Buenos Aires"


# ——— Pantallas y permisos ———


@pytest.mark.django_db
def test_ca21_sin_permiso_no_accede_a_ninguna_pantalla(client, subir):
    carga = subir(_fila())
    fila = carga.filas.get()
    sin_permiso = User.objects.create_user(username="sin-permiso", password="x")
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
        reverse("carga_masiva_fila_quitar", args=[carga.pk, fila.pk]),
    ):
        assert client.post(url).status_code == 403, url

    carga.refresh_from_db()
    assert carga.esta_pendiente


@pytest.mark.django_db
def test_flujo_completo_por_pantallas(client, provincia, padron, usuario):
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
    rechazo = client.post(
        reverse("carga_masiva_confirmar", args=[carga.pk]), follow=True
    )
    assert "encontró filas con error" in rechazo.content.decode()

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
def test_ca22_formulario_y_detalle_muestran_observaciones(client, provincia, usuario):
    client.force_login(usuario)
    formulario = client.get(reverse("beneficiarios_crear"))
    assert 'name="observaciones"' in formulario.content.decode()

    beneficiario = _crear_preinscripto(
        _crear_titular(), observaciones="Necesita acompañante"
    )
    detalle = client.get(reverse("beneficiarios_detail", args=[beneficiario.pk]))
    assert "Necesita acompañante" in detalle.content.decode()
