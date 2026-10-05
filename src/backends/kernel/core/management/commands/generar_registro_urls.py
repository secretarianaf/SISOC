"""Regenera ``src/backends/config/url_registry.json`` desde la composición completa."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import get_resolver

from core.url_registry import REGISTRY_PATH, generar


class Command(BaseCommand):
    help = (
        "Regenera src/backends/config/url_registry.json (requiere config.settings_all)."
    )

    def handle(self, *args, **options):
        if settings.ROOT_URLCONF != "config.urls_all":
            raise CommandError(
                "Correr con DJANGO_SETTINGS_MODULE=config.settings_all: el "
                "registro describe la composición completa."
            )
        entradas = generar(get_resolver().url_patterns)
        REGISTRY_PATH.write_text(
            json.dumps(entradas, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(f"{len(entradas)} nombres en {REGISTRY_PATH}")
