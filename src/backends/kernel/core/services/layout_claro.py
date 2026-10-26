"""Contexto del layout claro (includes/base_claro.html): cabecera blanca con
breadcrumb, iniciales y rol del usuario. Lo usa Inspecciones escolares."""


def iniciales(nombre):
    """Hasta dos iniciales en mayúscula para el avatar; "?" si no hay nombre."""
    partes = [parte for parte in (nombre or "").split() if parte]
    letras = "".join(parte[0] for parte in partes[:2]).upper()
    return letras or "?"


def rol_para_cabecera(usuario):
    """Rol de Inspecciones si lo tiene; si no, el rol libre del perfil; si no, vacío."""
    perfil = getattr(usuario, "profile", None)
    if perfil is None:
        return ""
    mostrar = getattr(perfil, "get_inspecciones_rol_display", None)
    if mostrar and getattr(perfil, "inspecciones_rol", ""):
        return mostrar()
    return getattr(perfil, "rol", "") or ""


def contexto_layout_claro(usuario, migas):
    """``migas``: lista de ``{"text", "url"?}``; el último ítem es la página actual."""
    return {
        "breadcrumb_items": migas,
        "iniciales_usuario": iniciales(
            usuario.get_full_name() or usuario.get_username()
        ),
        "rol_usuario": rol_para_cabecera(usuario),
        "ocultar_volver": True,
    }
