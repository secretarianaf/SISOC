"""URLConf reducido: solo las rutas de API que consume el front v2.

El schema completo del proyecto son ~21.700 lineas y 233 rutas, con errores de
`drf-spectacular` en apps que el front v2 no toca. Versionar eso haria que
cualquier cambio en una API ajena rompiera el chequeo de contrato de `/v2/`.

`docs/implementaciones/frontend_v2.md` ya preveia este recorte ("Filtrado del
schema versionado a las rutas que consume /v2/").

Se usa solo para generar el contrato, nunca para servir:

    python manage.py spectacular \\
        --urlconf config.urls_frontend_v2 \\
        --file frontends/packages/api/openapi.yaml

Al migrar un modulo nuevo a `/v2/` se agrega aca su `api_urls`.
"""

from django.urls import include, path

urlpatterns = [
    path("api/celiaquia/", include("celiaquia.api_urls")),
]
