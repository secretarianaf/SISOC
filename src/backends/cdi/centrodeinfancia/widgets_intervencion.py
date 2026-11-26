"""Widgets of the CDI intervention form."""

from django import forms
from django.urls import reverse


class _EnlaceDescarga:
    """Stands in for the stored file in the widget template: same name, authenticated URL."""

    def __init__(self, archivo, url):
        self._archivo = archivo
        self.url = url

    def __str__(self):
        return str(self._archivo)

    def __bool__(self):
        return bool(self._archivo)


class DocumentacionIntervencionWidget(forms.ClearableFileInput):
    """``ClearableFileInput`` whose current-file link is the authenticated download.

    CDI documentation is not served from ``/media/`` (nginx blocks it), so the stock
    ``FieldFile.url`` link answers 404. Replace and clear behave as in the stock widget.
    """

    def __init__(self, *args, intervencion_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.intervencion_pk = intervencion_pk

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.intervencion_pk and context["widget"]["is_initial"]:
            context["widget"]["value"] = _EnlaceDescarga(
                value,
                reverse(
                    "centrodeinfancia_web_intervencion_documentacion",
                    args=[self.intervencion_pk],
                ),
            )
        return context
