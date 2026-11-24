"""Alcance del usuario sobre el comedor de las vistas web de registros.

Relevamientos, seguimientos, seguimientos PNUD y actas cuelgan del comedor y no
tienen programa propio: si el comedor queda fuera del alcance del usuario (rol,
territorio o programa) la vista responde 404.
"""

from django.http import Http404

from comedores.services.comedor_service import ComedorService


def resolver_comedor_en_alcance(user, comedor_pk):
    """Comedor ``comedor_pk`` si el usuario lo alcanza; si no, ``Http404``."""
    pk = str(comedor_pk).strip()
    if not pk.isdigit():
        raise Http404("Comedor no encontrado.")
    return ComedorService.get_scoped_comedor_or_404(int(pk), user)


class ComedorAlcanceMixin:
    """Valida el alcance sobre ``comedor_pk`` antes de despachar la vista.

    Va después de ``LoginRequiredMixin`` para que un anónimo siga yendo al login.
    """

    def dispatch(self, request, *args, **kwargs):
        resolver_comedor_en_alcance(request.user, self.kwargs["comedor_pk"])
        return super().dispatch(request, *args, **kwargs)
