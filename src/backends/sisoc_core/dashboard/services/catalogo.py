"""Sincronización conservadora del catálogo administrado por código."""

import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction

from dashboard.models import Tablero

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo" / "tableros.json"
CAMPOS_TECNICOS = ("url", "ruta_interna")


def leer_catalogo():
    with CATALOGO.open(encoding="utf-8") as archivo:
        return json.load(archivo)


@transaction.atomic
def sincronizar_catalogo(entradas):
    """Reconcilia solo identidades inequívocas y conserva los campos operativos."""
    pks = set()
    slugs = set()
    for entrada in entradas:
        campos = entrada.get("fields", {})
        pk = entrada.get("pk")
        slug = campos.get("slug")
        identidad_invalida = (
            entrada.get("model") != "dashboard.tablero"
            or not isinstance(pk, int)
            or pk <= 0
            or not isinstance(slug, str)
            or not slug
        )
        if identidad_invalida or pk in pks or slug in slugs:
            raise ValidationError(
                "El catálogo contiene una identidad inválida o duplicada."
            )
        pks.add(pk)
        slugs.add(slug)
        por_pk = Tablero.objects.select_for_update().filter(pk=pk).first()
        por_slug = Tablero.objects.select_for_update().filter(slug=slug).first()
        if (por_pk and por_pk.slug != slug) or (por_slug and por_slug.pk != pk):
            raise ValidationError(
                "El catálogo contiene una identidad que requiere revisión."
            )
        if por_pk is None:
            Tablero.objects.create(pk=pk, **campos)
        else:
            cambios = []
            for nombre in CAMPOS_TECNICOS:
                if nombre in campos and getattr(por_pk, nombre) != campos[nombre]:
                    setattr(por_pk, nombre, campos[nombre])
                    cambios.append(nombre)
            if cambios:
                por_pk.save(update_fields=cambios)
    return len(entradas)


def sincronizar_catalogo_post_fixture():
    try:
        cantidad = sincronizar_catalogo(leer_catalogo())
    except ValidationError:
        return "⚠️ Catálogo de tableros sin sincronizar: revisar identidades."
    return f"✅ Catálogo de tableros sincronizado: {cantidad} entradas."
