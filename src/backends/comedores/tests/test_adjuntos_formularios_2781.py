"""#2781: documentos (imagen o PDF) adjuntos a los formularios de relevamiento.

API territorial ``/api/territorial/comedores/{id}/adjuntos/`` y lista en el
detalle web de cada formulario.
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    ArchivoAdjunto,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)
from relevamientos.services import adjuntos as adjuntos_service
from users.models import TerritorialComedorProvincia

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture(autouse=True)
def _media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _imagen(nombre="foto.png", formato="PNG", tipo="image/png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format=formato)
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type=tipo)


def _pdf(nombre="acta.pdf", contenido=PDF):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


def _territorial(username, provincia):
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    return user


def _api(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def zona(db):
    provincia = Provincia.objects.create(nombre="Prov adjuntos")
    comedor = Comedor.objects.create(nombre="Comedor adjuntos", provincia=provincia)
    user = _territorial("terr_adj", provincia)
    return comedor, user


def _formularios(comedor, user):
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=user
    )
    return {
        "relevamiento": relevamiento,
        "seguimiento": PrimerSeguimiento.objects.create(id_relevamiento=relevamiento),
        "seguimiento_pnud": SeguimientoPnud.objects.create(
            comedor=comedor, tecnico=user, formulario="iia", client_uuid="pnud-adj"
        ),
        "acta": ActaComplementaria.objects.create(comedor=comedor, tecnico=user),
    }


def _url(comedor, adjunto_id=None):
    base = f"/api/territorial/comedores/{comedor.id}/adjuntos/"
    return f"{base}{adjunto_id}/" if adjunto_id else base


def _subir(client, comedor, tipo, formulario_id, archivo, **extra):
    datos = {
        "archivo": archivo,
        "formulario_tipo": tipo,
        "formulario_id": formulario_id,
        **extra,
    }
    return client.post(_url(comedor), datos, format="multipart")


@pytest.mark.parametrize(
    "tipo", ["relevamiento", "seguimiento", "seguimiento_pnud", "acta"]
)
def test_sube_un_pdf_a_cada_tipo_de_formulario(zona, tipo):
    comedor, user = zona
    formulario = _formularios(comedor, user)[tipo]

    response = _subir(_api(user), comedor, tipo, formulario.pk, _pdf())

    assert response.status_code == 201
    (item,) = response.json()["adjuntos"]
    assert set(item) == {
        "id",
        "nombre",
        "tipo_mime",
        "tamano",
        "url",
        "formulario_tipo",
        "formulario_id",
        "client_uuid",
        "fecha_subida",
    }
    assert item["nombre"] == "acta.pdf"
    assert item["tipo_mime"] == "application/pdf"
    assert item["tamano"] == len(PDF)
    assert item["formulario_tipo"] == tipo
    assert item["formulario_id"] == formulario.pk
    assert item["url"].startswith("http") and "/adjuntos/" in item["url"]
    adjunto = ArchivoAdjunto.objects.get()
    assert adjunto.subido_por == user
    assert adjunto.comedor == comedor
    assert adjunto.archivo.name.startswith(f"adjuntos/{comedor.id}/")
    assert adjunto.archivo.name.endswith(".pdf")


@pytest.mark.parametrize(
    "nombre, formato, tipo_mime",
    [
        ("a.jpg", "JPEG", "image/jpeg"),
        ("a.jpeg", "JPEG", "image/jpeg"),
        ("a.png", "PNG", "image/png"),
        ("a.webp", "WEBP", "image/webp"),
    ],
)
def test_acepta_los_formatos_de_imagen(zona, nombre, formato, tipo_mime):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]

    response = _subir(
        _api(user),
        comedor,
        "relevamiento",
        relevamiento.pk,
        _imagen(nombre, formato, tipo_mime),
    )

    assert response.status_code == 201
    assert response.json()["adjuntos"][0]["tipo_mime"] == tipo_mime


def test_lista_trae_los_adjuntos_del_formulario(zona):
    comedor, user = zona
    formularios = _formularios(comedor, user)
    client = _api(user)
    _subir(client, comedor, "relevamiento", formularios["relevamiento"].pk, _pdf())
    _subir(client, comedor, "acta", formularios["acta"].pk, _pdf("otra.pdf"))

    response = client.get(
        _url(comedor),
        {"formulario_tipo": "acta", "formulario_id": formularios["acta"].pk},
    )

    assert response.status_code == 200
    assert [a["nombre"] for a in response.json()["adjuntos"]] == ["otra.pdf"]


def test_lista_exige_formulario_valido(zona):
    comedor, user = zona
    client = _api(user)

    assert client.get(_url(comedor)).status_code == 400
    sin_id = client.get(_url(comedor), {"formulario_tipo": "acta"})
    assert sin_id.status_code == 400
    assert "formulario_id" in sin_id.json()["detail"]


def test_reintento_con_el_mismo_client_uuid_es_idempotente(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    client = _api(user)

    primero = _subir(
        client, comedor, "relevamiento", relevamiento.pk, _pdf(), client_uuid="u-1"
    )
    segundo = _subir(
        client, comedor, "relevamiento", relevamiento.pk, _pdf(), client_uuid="u-1"
    )

    assert primero.status_code == 201
    assert segundo.status_code == 200
    assert len(segundo.json()["adjuntos"]) == 1
    assert segundo.json()["adjuntos"][0]["client_uuid"] == "u-1"
    assert ArchivoAdjunto.objects.count() == 1


def test_rechaza_por_contenido_gif_svg_y_texto_aunque_el_nombre_sea_valido(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    gif = _imagen("foto.png", "GIF", "image/png")

    for archivo in (
        gif,
        SimpleUploadedFile("dibujo.png", b"<svg/>", content_type="image/png"),
        SimpleUploadedFile("nota.pdf", b"hola", content_type="application/pdf"),
        SimpleUploadedFile("virus.exe", b"MZ\x90\x00", content_type="x/y"),
    ):
        response = _subir(_api(user), comedor, "relevamiento", relevamiento.pk, archivo)
        assert response.status_code == 400, archivo.name
        assert "imagen" in response.json()["detail"]
    assert not ArchivoAdjunto.objects.exists()


@pytest.mark.parametrize("nombre", ["foto.jfif", "sinextension", "FOTO.JPE", "x.bin"])
def test_el_tipo_se_decide_por_contenido_no_por_nombre(zona, nombre):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]

    response = _subir(
        _api(user),
        comedor,
        "relevamiento",
        relevamiento.pk,
        _imagen(nombre, "JPEG", "application/octet-stream"),
    )

    assert response.status_code == 201
    adjunto = ArchivoAdjunto.objects.get()
    assert adjunto.archivo.name.endswith(".jpg")
    assert adjunto.tipo_mime == "image/jpeg"
    assert adjunto.nombre_original == nombre


def test_pdf_sin_extension_se_acepta_y_se_guarda_como_pdf(zona):
    comedor, user = zona
    acta = _formularios(comedor, user)["acta"]

    response = _subir(_api(user), comedor, "acta", acta.pk, _pdf("scan"))

    assert response.status_code == 201
    assert ArchivoAdjunto.objects.get().archivo.name.endswith(".pdf")


def test_rechaza_contenido_que_no_coincide_con_la_extension(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    client = _api(user)

    falso_pdf = _subir(
        client, comedor, "relevamiento", relevamiento.pk, _pdf(contenido=b"hola mundo")
    )
    falsa_imagen = _subir(
        client,
        comedor,
        "relevamiento",
        relevamiento.pk,
        SimpleUploadedFile("foto.png", b"<svg/>", content_type="image/png"),
    )

    assert falso_pdf.status_code == 400
    assert falsa_imagen.status_code == 400
    assert not ArchivoAdjunto.objects.exists()


def test_rechaza_archivo_vacio_o_ausente(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    client = _api(user)

    vacio = _subir(
        client, comedor, "relevamiento", relevamiento.pk, _pdf(contenido=b"")
    )
    ausente = client.post(
        _url(comedor),
        {"formulario_tipo": "relevamiento", "formulario_id": relevamiento.pk},
        format="multipart",
    )

    assert vacio.status_code == 400
    assert ausente.status_code == 400
    assert "archivo" in ausente.json()["detail"]


def test_rechaza_archivo_de_mas_de_10_mb(zona, monkeypatch):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    monkeypatch.setattr(adjuntos_service, "MAX_ADJUNTO_BYTES", len(PDF) - 1)

    response = _subir(_api(user), comedor, "relevamiento", relevamiento.pk, _pdf())

    assert response.status_code == 400
    assert "10 MB" in response.json()["detail"]
    assert not ArchivoAdjunto.objects.exists()


def test_limite_fijo_de_10_mb():
    assert adjuntos_service.MAX_ADJUNTO_BYTES == 10 * 1024 * 1024
    assert adjuntos_service.MAX_ADJUNTOS_POR_FORMULARIO == 10


def test_tope_de_10_archivos_por_formulario(zona):
    comedor, user = zona
    formularios = _formularios(comedor, user)
    client = _api(user)
    for indice in range(10):
        response = _subir(
            client,
            comedor,
            "relevamiento",
            formularios["relevamiento"].pk,
            _pdf(f"{indice}.pdf"),
        )
        assert response.status_code == 201

    onceavo = _subir(
        client, comedor, "relevamiento", formularios["relevamiento"].pk, _pdf("11.pdf")
    )
    otro_formulario = _subir(client, comedor, "acta", formularios["acta"].pk, _pdf())

    assert onceavo.status_code == 400
    assert "10" in onceavo.json()["detail"]
    assert otro_formulario.status_code == 201
    assert ArchivoAdjunto.objects.filter(formulario_tipo="relevamiento").count() == 10


def test_formulario_inexistente_o_de_otro_comedor_es_404(zona):
    comedor, user = zona
    otro = Comedor.objects.create(nombre="Otro", provincia=comedor.provincia)
    ajeno = _formularios(otro, user)["relevamiento"]
    client = _api(user)

    inexistente = _subir(client, comedor, "relevamiento", 999999, _pdf())
    de_otro_comedor = _subir(client, comedor, "relevamiento", ajeno.pk, _pdf())
    seguimiento_ajeno = _subir(
        client,
        comedor,
        "seguimiento",
        PrimerSeguimiento.objects.get(id_relevamiento=ajeno).pk,
        _pdf(),
    )

    assert inexistente.status_code == 404
    assert de_otro_comedor.status_code == 404
    assert seguimiento_ajeno.status_code == 404
    assert not ArchivoAdjunto.objects.exists()


def test_tipo_o_id_invalidos_son_400(zona):
    comedor, user = zona
    client = _api(user)

    assert _subir(client, comedor, "inventado", 1, _pdf()).status_code == 400
    assert _subir(client, comedor, "relevamiento", "abc", _pdf()).status_code == 400
    assert _subir(client, comedor, "relevamiento", "", _pdf()).status_code == 400


def test_comedor_fuera_de_la_zona_es_404_como_las_fotos(zona):
    comedor, user = zona
    otra_provincia = Provincia.objects.create(nombre="Otra prov")
    ajeno = Comedor.objects.create(nombre="Ajeno", provincia=otra_provincia)
    vecino = _territorial("terr_adj_vecino", otra_provincia)
    relevamiento = _formularios(ajeno, vecino)["relevamiento"]

    response = _subir(_api(user), ajeno, "relevamiento", relevamiento.pk, _pdf())

    assert response.status_code == 404
    assert not ArchivoAdjunto.objects.exists()


def test_usuario_sin_rol_territorial_es_403_y_sin_token_401(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    comun = get_user_model().objects.create_user(username="comun", password="x")

    assert (
        _subir(
            _api(comun), comedor, "relevamiento", relevamiento.pk, _pdf()
        ).status_code
        == 403
    )
    sin_token = APIClient().post(_url(comedor), {}, format="multipart")
    assert sin_token.status_code == 401


def test_borra_el_propio_adjunto_y_devuelve_la_lista(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    client = _api(user)
    _subir(client, comedor, "relevamiento", relevamiento.pk, _pdf("uno.pdf"))
    _subir(client, comedor, "relevamiento", relevamiento.pk, _pdf("dos.pdf"))
    adjunto = ArchivoAdjunto.objects.get(nombre_original="uno.pdf")
    ruta = adjunto.archivo.path

    response = client.delete(_url(comedor, adjunto.pk))

    assert response.status_code == 200
    assert [a["nombre"] for a in response.json()["adjuntos"]] == ["dos.pdf"]
    assert not ArchivoAdjunto.objects.filter(pk=adjunto.pk).exists()
    with pytest.raises(FileNotFoundError):
        open(ruta, "rb")  # pylint: disable=consider-using-with
    # Reintento del mismo DELETE: ya no existe.
    assert client.delete(_url(comedor, adjunto.pk)).status_code == 404


def test_no_borra_el_adjunto_de_otro_tecnico(zona):
    comedor, user = zona
    relevamiento = _formularios(comedor, user)["relevamiento"]
    _subir(_api(user), comedor, "relevamiento", relevamiento.pk, _pdf())
    adjunto = ArchivoAdjunto.objects.get()
    otro = _territorial("terr_adj_otro", comedor.provincia)

    response = _api(otro).delete(_url(comedor, adjunto.pk))

    assert response.status_code == 403
    assert ArchivoAdjunto.objects.filter(pk=adjunto.pk).exists()


def test_no_borra_si_el_formulario_esta_validado(zona):
    comedor, user = zona
    acta = _formularios(comedor, user)["acta"]
    _subir(_api(user), comedor, "acta", acta.pk, _pdf())
    acta.estado_validacion = ActaComplementaria.ESTADO_VALIDACION_VALIDADO
    acta.save(update_fields=["estado_validacion"])

    response = _api(user).delete(_url(comedor, ArchivoAdjunto.objects.get().pk))

    assert response.status_code == 409
    assert ArchivoAdjunto.objects.count() == 1


def test_no_sube_si_el_formulario_esta_validado(zona):
    comedor, user = zona
    acta = _formularios(comedor, user)["acta"]
    acta.estado_validacion = ActaComplementaria.ESTADO_VALIDACION_VALIDADO
    acta.save(update_fields=["estado_validacion"])

    response = _subir(_api(user), comedor, "acta", acta.pk, _pdf())

    assert response.status_code == 409
    assert response.json()["estado_validacion"] == "Validado"
    assert not ArchivoAdjunto.objects.exists()


def test_reintento_de_un_uuid_ya_subido_sigue_siendo_200_aunque_se_valide(zona):
    comedor, user = zona
    acta = _formularios(comedor, user)["acta"]
    client = _api(user)
    _subir(client, comedor, "acta", acta.pk, _pdf(), client_uuid="u-v")
    acta.estado_validacion = ActaComplementaria.ESTADO_VALIDACION_VALIDADO
    acta.save(update_fields=["estado_validacion"])

    response = _subir(client, comedor, "acta", acta.pk, _pdf(), client_uuid="u-v")

    assert response.status_code == 200


def test_client_uuid_de_otro_formulario_es_400(zona):
    comedor, user = zona
    formularios = _formularios(comedor, user)
    client = _api(user)
    _subir(
        client,
        comedor,
        "relevamiento",
        formularios["relevamiento"].pk,
        _pdf(),
        client_uuid="u-x",
    )

    response = _subir(
        client, comedor, "acta", formularios["acta"].pk, _pdf(), client_uuid="u-x"
    )

    assert response.status_code == 400
    assert "otro formulario" in response.json()["detail"]
    assert ArchivoAdjunto.objects.count() == 1


def test_el_listado_filtra_tambien_por_comedor(zona):
    comedor, user = zona
    otro = Comedor.objects.create(nombre="Otro 3", provincia=comedor.provincia)
    acta = _formularios(comedor, user)["acta"]
    ArchivoAdjunto.objects.create(
        comedor=otro,
        formulario_tipo="acta",
        formulario_id=acta.pk,
        archivo="adjuntos/x/a.pdf",
        nombre_original="a.pdf",
        tipo_mime="application/pdf",
        tamano=1,
    )

    assert not adjuntos_service.adjuntos_de(comedor.id, "acta", acta.pk).exists()
    assert adjuntos_service.adjuntos_de(otro.id, "acta", acta.pk).count() == 1


def test_no_borra_adjuntos_de_otro_comedor(zona):
    comedor, user = zona
    otro = Comedor.objects.create(nombre="Otro 2", provincia=comedor.provincia)
    acta = _formularios(otro, user)["acta"]
    _subir(_api(user), otro, "acta", acta.pk, _pdf())

    response = _api(user).delete(_url(comedor, ArchivoAdjunto.objects.get().pk))

    assert response.status_code == 404
    assert ArchivoAdjunto.objects.count() == 1


# --------------------------------------------------------------- detalle web


@pytest.fixture
def web(client, db):
    user = get_user_model().objects.create_superuser(
        username="admin_adj", email="admin_adj@example.com", password="x"
    )
    client.force_login(user)
    return client


def _urls_detalle(comedor, formularios):
    relevamiento = formularios["relevamiento"]
    return {
        "relevamiento": reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor.pk, "pk": relevamiento.pk},
        ),
        "seguimiento": reverse(
            "seguimiento_detalle",
            kwargs={
                "comedor_pk": comedor.pk,
                "relevamiento_pk": relevamiento.pk,
                "pk": formularios["seguimiento"].pk,
            },
        ),
        "seguimiento_pnud": reverse(
            "seguimiento_pnud_detalle",
            kwargs={"comedor_pk": comedor.pk, "pk": formularios["seguimiento_pnud"].pk},
        ),
        "acta": reverse(
            "acta_complementaria_detalle",
            kwargs={"comedor_pk": comedor.pk, "pk": formularios["acta"].pk},
        ),
    }


@pytest.mark.parametrize(
    "tipo", ["relevamiento", "seguimiento", "seguimiento_pnud", "acta"]
)
def test_el_detalle_web_lista_los_adjuntos_con_su_descarga(web, zona, tipo):
    comedor, user = zona
    formularios = _formularios(comedor, user)
    url = _urls_detalle(comedor, formularios)[tipo]
    assert "Archivos adjuntos" not in web.get(url).content.decode()
    _subir(_api(user), comedor, tipo, formularios[tipo].pk, _pdf("constancia-2781.pdf"))
    adjunto = ArchivoAdjunto.objects.get()

    response = web.get(url)

    html = response.content.decode()
    assert response.status_code == 200
    assert "Archivos adjuntos" in html
    assert "constancia-2781.pdf" in html
    descarga = reverse(
        "adjunto_descargar", kwargs={"comedor_pk": comedor.pk, "pk": adjunto.pk}
    )
    assert descarga in html
    assert adjunto.archivo.url not in html


def test_el_detalle_no_mezcla_adjuntos_de_otros_formularios(web, zona):
    comedor, user = zona
    formularios = _formularios(comedor, user)
    _subir(
        _api(user), comedor, "acta", formularios["acta"].pk, _pdf("solo-del-acta.pdf")
    )

    html = web.get(_urls_detalle(comedor, formularios)["relevamiento"]).content.decode()

    assert "solo-del-acta.pdf" not in html


# ------------------------------------------------------- descarga autenticada


def _adjunto_subido(zona, nombre="constancia.pdf"):
    comedor, user = zona
    acta = _formularios(comedor, user)["acta"]
    response = _subir(_api(user), comedor, "acta", acta.pk, _pdf(nombre))
    return comedor, ArchivoAdjunto.objects.get(), response


def _url_descarga(comedor, adjunto):
    return reverse(
        "adjunto_descargar", kwargs={"comedor_pk": comedor.pk, "pk": adjunto.pk}
    )


def test_la_url_de_la_api_apunta_a_la_descarga_autenticada(zona):
    comedor, adjunto, response = _adjunto_subido(zona)

    url = response.json()["adjuntos"][0]["url"]

    assert url == "http://testserver" + _url_descarga(comedor, adjunto)
    assert "/media/" not in url


def test_descarga_anonima_no_entrega_el_archivo(client, zona):
    comedor, adjunto, _ = _adjunto_subido(zona)

    response = client.get(_url_descarga(comedor, adjunto))

    assert response.status_code in (302, 403)
    assert b"%PDF" not in b"".join(getattr(response, "streaming_content", []))


def test_descarga_sin_permiso_es_403(client, zona):
    comedor, adjunto, _ = _adjunto_subido(zona)
    sin_permiso = get_user_model().objects.create_user(username="sinperm", password="x")
    client.force_login(sin_permiso)

    assert client.get(_url_descarga(comedor, adjunto)).status_code == 403


def test_descarga_con_permiso_es_attachment_con_nosniff(client, zona):
    comedor, adjunto, _ = _adjunto_subido(zona, "constancia-2781.pdf")
    lector = get_user_model().objects.create_user(username="lector", password="x")
    lector.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    client.force_login(lector)

    response = client.get(_url_descarga(comedor, adjunto))

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    assert "constancia-2781.pdf" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Type"] == "application/pdf"
    assert b"".join(response.streaming_content) == PDF


def test_descarga_con_comedor_equivocado_es_404(client, zona, web):
    comedor, adjunto, _ = _adjunto_subido(zona)
    otro = Comedor.objects.create(nombre="Otro 4", provincia=comedor.provincia)

    assert web.get(_url_descarga(otro, adjunto)).status_code == 404
