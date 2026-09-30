from django.urls import path

from ver_para_ser_libre import api_views

urlpatterns = [
    path("session/", api_views.rest_session, name="vpsl_api_session"),
    path("options/", api_views.rest_options, name="vpsl_api_options"),
    path("itinerarios/", api_views.rest_itinerarios, name="vpsl_api_itinerarios"),
    path(
        "itinerarios/<int:pk>/",
        api_views.rest_itinerario_detail,
        name="vpsl_api_itinerario_detail",
    ),
    path(
        "jornadas/<int:pk>/",
        api_views.rest_jornada_detail,
        name="vpsl_api_jornada_detail",
    ),
    path(
        "jornadas/<int:pk>/registros/",
        api_views.rest_registros,
        name="vpsl_api_registros",
    ),
    path(
        "jornadas/<int:pk>/laboratorio/",
        api_views.rest_laboratorio,
        name="vpsl_api_laboratorio",
    ),
    path("sedes/", api_views.rest_sedes, name="vpsl_api_sedes"),
    path("sedes/<int:pk>/", api_views.rest_sede_detail, name="vpsl_api_sede_detail"),
    path("forms/<str:kind>/<int:pk>/", api_views.rest_form, name="vpsl_api_form"),
    path("actions/<str:kind>/<int:pk>/", api_views.rest_action, name="vpsl_api_action"),
    path("renaper/", api_views.rest_renaper, name="vpsl_api_renaper"),
    path("ubicacion/", api_views.rest_ubicacion, name="vpsl_api_ubicacion"),
    path("exports/<str:kind>/<int:pk>/", api_views.rest_export, name="vpsl_api_export"),
]
