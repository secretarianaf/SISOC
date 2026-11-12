from types import SimpleNamespace

from ciudadanos import api


def test_prevalidar_ciudadano_existente_expone_datos_sin_modelo(mocker):
    ciudadano = SimpleNamespace(
        documento=12345678,
        nombre="Ana",
        apellido="Pérez",
        sexo="Femenino",
        fecha_nacimiento=None,
        edad=30,
        telefono="",
        pk=11,
    )
    mocker.patch("ciudadanos.api._buscar_ciudadano_verificado", return_value=ciudadano)

    resultado = api.prevalidar_ciudadano_renaper("12345678")

    assert resultado["success"] is True
    assert resultado["data"]["ciudadano_id"] == 11
    assert "ciudadano" not in resultado


def test_resolver_ciudadano_crea_y_expone_resumen(mocker):
    mocker.patch(
        "ciudadanos.api.prevalidar_ciudadano_renaper",
        return_value={
            "success": True,
            "pending_creation": True,
            "data": {"dni": 12345678},
            "datos_api": {"origen": "fake"},
        },
    )
    mocker.patch(
        "ciudadanos.api._datos_para_ciudadano",
        return_value=({"nombre": "Ana"}, None),
    )
    ciudadano = SimpleNamespace(
        documento=12345678,
        nombre="Ana",
        apellido="Pérez",
        sexo="Femenino",
        fecha_nacimiento=None,
        edad=30,
        telefono="",
        pk=12,
    )
    crear = mocker.patch(
        "ciudadanos.api.Ciudadano.objects.create", return_value=ciudadano
    )

    resultado = api.resolver_ciudadano_renaper("12345678")

    crear.assert_called_once_with(nombre="Ana")
    assert resultado["success"] is True
    assert resultado["data"]["ciudadano_id"] == 12


def test_resolver_ciudadano_rechaza_dni_invalido_de_renaper(mocker):
    mocker.patch(
        "ciudadanos.api.prevalidar_ciudadano_renaper",
        return_value={
            "success": True,
            "pending_creation": True,
            "data": {
                "dni": "no-es-un-dni",
                "nombre": "Ana",
                "apellido": "Pérez",
                "fecha_nacimiento": "2000-01-01",
            },
        },
    )

    resultado = api.resolver_ciudadano_renaper("12345678")

    assert resultado == {
        "success": False,
        "message": "RENAPER devolvió un DNI inválido.",
    }


def test_obtener_datos_para_formulario_conserva_las_claves_de_relacion(mocker):
    mocker.patch(
        "ciudadanos.api.consultar_ciudadano_renaper",
        return_value={
            "success": True,
            "message": "Datos obtenidos desde RENAPER.",
            "data": {"dni": "12345678"},
            "datos_api": {"origen": "fake"},
        },
    )
    mocker.patch(
        "ciudadanos.api.construir_datos_ciudadano_desde_renaper",
        return_value=(
            {
                "nombre": "Ana",
                "sexo_id": 2,
                "nacionalidad_id": 3,
            },
            None,
        ),
    )

    resultado = api.obtener_datos_ciudadano_desde_renaper("12345678")

    assert resultado["success"] is True
    assert resultado["data"] == {
        "nombre": "Ana",
        "sexo": 2,
        "nacionalidad": 3,
    }
    assert resultado["datos_api"] == {"origen": "fake"}


def test_consulta_por_dni_usa_un_solo_cliente_con_tope_total(mocker):
    """#2889: un login para los tres sexos y un tope por debajo del proxy."""
    mocker.patch.object(api.time, "monotonic", return_value=1000.0)
    consultar = mocker.patch(
        "ciudadanos.api.consultar_datos_renaper",
        return_value={"success": False, "error": "Sin datos", "error_type": "no_match"},
    )

    resultado = api._consultar_por_dni("30111222", None)

    assert resultado == {"success": False, "error": "Sin datos"}
    assert [llamada.args for llamada in consultar.call_args_list] == [
        ("30111222", "M"),
        ("30111222", "F"),
        ("30111222", "X"),
    ]
    clientes = {id(llamada.kwargs["client"]) for llamada in consultar.call_args_list}
    assert len(clientes) == 1
    client = consultar.call_args.kwargs["client"]
    assert client.reuse_token is True
    assert client.deadline == 1000.0 + api.PRESUPUESTO_CONSULTA_RENAPER_SEGUNDOS
    assert api.PRESUPUESTO_CONSULTA_RENAPER_SEGUNDOS < 25


def test_consulta_por_dni_corta_ante_un_timeout(mocker):
    consultar = mocker.patch(
        "ciudadanos.api.consultar_datos_renaper",
        return_value={
            "success": False,
            "error": "RENAPER no respondio a tiempo durante la consulta.",
            "error_type": "timeout",
        },
    )

    resultado = api._consultar_por_dni("30111222", None)

    assert consultar.call_count == 1
    assert resultado["success"] is False
    assert "no respondio a tiempo" in resultado["error"]
