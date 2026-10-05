import pytest
from django.db import OperationalError
from rest_framework.test import APIRequestFactory

from VAT.api_web_views import VatWebPavViewSet
from VAT.services import pav_service
from VAT.services.pav_service import PavService

URL = "/api/vat/web/pav/"


def _registro(numero):
    return {
        "pav_cursada_key": numero,
        "ciudadano_key": 101,
        "pav_curso_key": numero,
        "pav_curso_desc": f"Curso {numero}",
    }


def _listar(query, mocker, permitir=True):
    if permitir:
        mocker.patch.object(VatWebPavViewSet, "permission_classes", [])
    request = APIRequestFactory().get(URL, query)
    return VatWebPavViewSet.as_view({"get": "list"})(request)


@pytest.mark.parametrize(
    "query, mensaje",
    [
        ({}, "Este parametro es requerido."),
        ({"documento": "  "}, "Este parametro es requerido."),
        ({"documento": "30.111.222"}, "El documento debe ser numerico."),
        ({"documento": "abc"}, "El documento debe ser numerico."),
        ({"documento": "١٢٣٤٥٦٧٨"}, "El documento debe ser numerico."),
        ({"documento": "99999999999999999999"}, "El documento es demasiado largo."),
    ],
)
def test_pav_documento_invalido_devuelve_400_sin_consultar_dw(query, mensaje, mocker):
    listar_mock = mocker.patch.object(PavService, "listar_por_documento")

    response = _listar(query, mocker)

    assert response.status_code == 400
    assert response.data == {"documento": [mensaje]}
    listar_mock.assert_not_called()


def test_pav_sin_credenciales_rechaza_sin_consultar_dw(mocker):
    listar_mock = mocker.patch.object(PavService, "listar_por_documento")

    response = _listar({"documento": "30111222"}, mocker, permitir=False)

    assert response.status_code in (401, 403)
    listar_mock.assert_not_called()


def test_pav_devuelve_registros_paginados(mocker):
    registros = [_registro(numero) for numero in range(1, 13)]
    listar_mock = mocker.patch.object(
        PavService, "listar_por_documento", return_value=registros
    )

    response = _listar({"documento": " 30111222 "}, mocker)

    assert response.status_code == 200
    listar_mock.assert_called_once_with("30111222")
    assert response.data["count"] == 12
    assert response.data["results"] == registros[:10]
    assert response.data["next"] is not None
    assert response.data["previous"] is None


def test_pav_vista_navegable_html_renderiza_sin_queryset(mocker):
    mocker.patch.object(PavService, "listar_por_documento", return_value=[_registro(1)])
    mocker.patch.object(VatWebPavViewSet, "permission_classes", [])
    request = APIRequestFactory().get(
        URL, {"documento": "30111222"}, HTTP_ACCEPT="text/html"
    )

    response = VatWebPavViewSet.as_view({"get": "list"})(request)
    response.render()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")


def test_pav_documento_sin_registros_devuelve_lista_vacia(mocker):
    mocker.patch.object(PavService, "listar_por_documento", return_value=[])

    response = _listar({"documento": "30111222"}, mocker)

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


def _mock_cursor(mocker):
    cursor = mocker.MagicMock()
    connection_mock = mocker.patch.object(pav_service, "connection")
    connection_mock.cursor.return_value.__enter__.return_value = cursor
    return cursor


def test_pav_service_arma_un_dict_por_fila_con_la_descripcion_del_curso(mocker):
    cursor = _mock_cursor(mocker)
    cursor.description = [("ciudadano_key",), ("pav_curso_key",), ("pav_curso_desc",)]
    cursor.fetchall.return_value = [
        (101, 7, "Huerta"),
        (101, 9, None),
    ]

    registros = PavService.listar_por_documento("30111222")

    assert registros == [
        {"ciudadano_key": 101, "pav_curso_key": 7, "pav_curso_desc": "Huerta"},
        {"ciudadano_key": 101, "pav_curso_key": 9, "pav_curso_desc": None},
    ]
    sql, params = cursor.execute.call_args.args
    assert params == [30111222]
    assert "FROM DW_sisoc.DIM_Ciudadanos_Ciudadano d" in sql
    assert "JOIN DW_sisoc.FCT_PAV f ON f.ciudadano_key = d.ciudadano_key" in sql
    assert "LEFT JOIN DW_sisoc.DIM_PAV_Cursos" in sql
    assert "WHERE d.documento = %s" in sql


def test_pav_service_consulta_columnas_explicitas_ordenadas_y_con_tiempo_maximo(
    mocker,
):
    cursor = _mock_cursor(mocker)
    cursor.description = []
    cursor.fetchall.return_value = []

    PavService.listar_por_documento("30111222")

    sql = cursor.execute.call_args.args[0]
    assert "f.*" not in sql
    for columna in pav_service.COLUMNAS_PAV:
        assert f"f.{columna}" in sql
    assert "c.pav_curso_desc" in sql
    assert "ORDER BY f.fecha_inscripcion DESC, f.pav_cursada_key DESC" in sql
    assert "MAX_EXECUTION_TIME(5000)" in sql


def test_pav_service_propaga_el_error_de_base(mocker):
    cursor = _mock_cursor(mocker)
    cursor.execute.side_effect = OperationalError(1049, "Unknown database")

    with pytest.raises(OperationalError):
        PavService.listar_por_documento("30111222")
