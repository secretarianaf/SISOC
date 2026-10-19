"""Conserva el multipart del ABM antes de que CSRF lea su stream."""

from django.utils.deprecation import MiddlewareMixin


class UserAdminBodyMiddleware(MiddlewareMixin):
    """Sólo dos vistas resueltas por el servidor; mantiene CSRF sin exenciones."""

    def process_view(self, request, _view_func, _view_args, _view_kwargs):
        match = request.resolver_match
        if (
            request.method == "POST"
            and match is not None
            and match.url_name
            in {
                "usuario_crear",
                "usuario_editar",
            }
        ):
            # Propiedad de Django: conserva bytes idénticos, aplica el límite de
            # memoria del framework y permite a CSRF procesar el mismo cuerpo.
            # Sin persistencia, reconstrucción del formulario ni logs del body.
            request.body  # pylint: disable=pointless-statement
