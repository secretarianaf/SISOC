import re

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.functions import Lower

from core.models import Dia
from core.services.text_encoding import normalize_text
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA

# Clave de cada grupo de horario en el POST; arma el nombre schedule_dias_<clave>.
_CLAVE_GRUPO_RE = re.compile(r"[A-Za-z0-9_-]{1,20}")


def _format_activity_schedule(start_time, end_time):
    if start_time and end_time:
        return f"{start_time:%H:%M} a {end_time:%H:%M}"
    if start_time:
        return start_time.strftime("%H:%M")
    return ""


class ActividadEspacioPWAWebForm(forms.ModelForm):
    categoria = forms.ChoiceField(
        label="Categoría",
        required=False,  # Compatibilidad con POST anteriores sin categoría.
        widget=forms.Select(attrs={"class": "form-control", "required": True}),
    )

    class Meta:
        model = ActividadEspacioPWA
        fields = (
            "catalogo_actividad",
            "nombre_fantasia",
            "cantidad_personas",
            "responsable_actividad",
            "vigencia_actividad_meses",
        )
        labels = {
            "catalogo_actividad": "Actividad",
            "nombre_fantasia": "Nombre de fantasía",
            "cantidad_personas": "Número de personas",
            "responsable_actividad": "Responsable",
            "vigencia_actividad_meses": "Vigencia en meses",
        }
        widgets = {
            "catalogo_actividad": forms.Select(attrs={"class": "form-control"}),
            "nombre_fantasia": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad_personas": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "1"}
            ),
            "responsable_actividad": forms.TextInput(attrs={"class": "form-control"}),
            "vigencia_actividad_meses": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
        }

    def __init__(self, *args, comedor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.comedor = comedor
        self._schedule_data = []
        self.schedule_errors = []
        catalogo = CatalogoActividadPWA.objects.filter(
            Q(activo=True) | Q(pk=self.instance.catalogo_actividad_id)
        ).order_by(Lower("actividad"), "id")
        self.fields["catalogo_actividad"].queryset = catalogo
        self.fields["catalogo_actividad"].label_from_instance = (
            lambda obj: obj.actividad
        )
        self.activity_options = list(catalogo.values("id", "categoria", "actividad"))
        categorias = sorted(
            {item["categoria"] for item in self.activity_options}, key=normalize_text
        )
        self.fields["categoria"].choices = [("", "Seleccionar")] + [
            (categoria, categoria) for categoria in categorias
        ]
        if self.instance.catalogo_actividad_id:
            self.initial["categoria"] = self.instance.catalogo_actividad.categoria
        self.day_options = list(Dia.objects.order_by("id"))
        self.schedule_rows = self._get_initial_schedule_rows()

    def _get_initial_schedule_rows(self):
        """Grupos de horario: varios días comparten una misma hora de inicio y fin."""
        if self.is_bound:
            return self._get_bound_schedule_rows()
        if self.instance and self.instance.pk:
            dia_id = self.instance.dia_actividad_id
            return [
                {
                    "key": "0",
                    "dias": [str(dia_id)] if dia_id else [],
                    "hora_inicio": (
                        self.instance.hora_inicio.strftime("%H:%M")
                        if self.instance.hora_inicio
                        else ""
                    ),
                    "hora_fin": (
                        self.instance.hora_fin.strftime("%H:%M")
                        if self.instance.hora_fin
                        else ""
                    ),
                }
            ]
        return [{"key": "0", "dias": [], "hora_inicio": "", "hora_fin": ""}]

    def _getlist(self, field_name):
        if hasattr(self.data, "getlist"):
            return self.data.getlist(field_name)
        value = self.data.get(field_name, [])
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value] if value else []

    def _get_bound_schedule_rows(self):
        """Lee los grupos del POST.

        Cada grupo manda ``schedule_grupo`` (su clave), sus días marcados en
        ``schedule_dias_<clave>`` y una hora de inicio y fin en el mismo orden.
        Sin ``schedule_grupo`` se acepta el formato anterior: un día por fila en
        ``schedule_dia_actividad``.
        """
        grupos = self._getlist("schedule_grupo")
        horas_inicio = self._getlist("schedule_hora_inicio")
        horas_fin = self._getlist("schedule_hora_fin")
        if grupos:
            claves = [
                clave if _CLAVE_GRUPO_RE.fullmatch(clave or "") else ""
                for clave in grupos
            ]
            dias_por_grupo = [
                self._getlist(f"schedule_dias_{clave}") if clave else []
                for clave in claves
            ]
        else:
            dias_legacy = self._getlist("schedule_dia_actividad")
            total = max(len(dias_legacy), len(horas_inicio), len(horas_fin), 1)
            claves = [str(index) for index in range(total)]
            dias_por_grupo = [
                (
                    [dias_legacy[index]]
                    if index < len(dias_legacy) and dias_legacy[index]
                    else []
                )
                for index in range(total)
            ]
        rows = []
        for index, clave in enumerate(claves):
            rows.append(
                {
                    "key": clave or str(index),
                    "dias": [str(dia) for dia in dias_por_grupo[index] if dia],
                    "hora_inicio": (
                        horas_inicio[index] if index < len(horas_inicio) else ""
                    ),
                    "hora_fin": horas_fin[index] if index < len(horas_fin) else "",
                }
            )
        return rows

    def clean_vigencia_actividad_meses(self):
        value = self.cleaned_data.get("vigencia_actividad_meses")
        if value is not None and value < 1:
            raise forms.ValidationError("La vigencia debe ser mayor a 0 meses.")
        return value

    def clean(self):
        cleaned = super().clean()
        catalogo_actividad = cleaned.get("catalogo_actividad")
        self._validar_categoria(catalogo_actividad, cleaned.get("categoria"))
        self._schedule_data = []
        self.schedule_errors = [{} for _ in self.schedule_rows]
        parsed_rows = []

        for index, row in enumerate(self.schedule_rows):
            row_errors = self.schedule_errors[index]
            dias = self._clean_schedule_days(row.get("dias"))
            hora_inicio = self._clean_schedule_time(
                row.get("hora_inicio"),
                "Hora inicio",
            )
            hora_fin = self._clean_schedule_time(row.get("hora_fin"), "Hora fin")

            if isinstance(dias, ValidationError):
                row_errors["dias"] = dias.message
                dias = []
            if isinstance(hora_inicio, ValidationError):
                row_errors["hora_inicio"] = hora_inicio.message
                hora_inicio = None
            if isinstance(hora_fin, ValidationError):
                row_errors["hora_fin"] = hora_fin.message
                hora_fin = None

            if hora_inicio and hora_fin and hora_fin <= hora_inicio:
                row_errors["hora_fin"] = (
                    "La hora de fin debe ser posterior a la hora de inicio."
                )

            if row_errors:
                continue

            # Cada día marcado se guarda como una actividad con el mismo horario.
            for dia_actividad in dias:
                parsed_rows.append(
                    {
                        "dia_actividad": dia_actividad,
                        "hora_inicio": hora_inicio,
                        "hora_fin": hora_fin,
                    }
                )

        if any(self.schedule_errors):
            self.add_error(
                None,
                "Completá cada horario: elegí al menos un día y las horas con "
                "formato HH:MM.",
            )
            return cleaned

        if not parsed_rows:
            self.add_error(None, "Agrega al menos un dia y horario.")
            return cleaned

        unique_rows = []
        seen_rows = set()
        for row in parsed_rows:
            key = (
                row["dia_actividad"].id,
                row["hora_inicio"].strftime("%H:%M"),
                row["hora_fin"].strftime("%H:%M"),
            )
            if key in seen_rows:
                continue
            seen_rows.add(key)
            unique_rows.append(row)

        if self._has_schedule_overlap(unique_rows):
            self.add_error(
                None,
                "La misma actividad no puede tener horarios cruzados en el mismo dia.",
            )

        if (
            self.comedor
            and catalogo_actividad
            and self._has_existing_schedule_overlap(unique_rows, catalogo_actividad)
        ):
            self.add_error(
                None,
                "Ya existe la misma actividad con un horario que se pisa ese dia.",
            )

        self._schedule_data = unique_rows

        return cleaned

    def _validar_categoria(self, catalogo_actividad, categoria):
        if (
            catalogo_actividad
            and categoria
            and catalogo_actividad.categoria != categoria
        ):
            self.add_error(
                "catalogo_actividad",
                "Selecciona una actividad de la categoría elegida.",
            )

    def _clean_schedule_days(self, values):
        if not values:
            return ValidationError("Seleccioná al menos un día.")
        try:
            ids = {int(value) for value in values}
        except (ValueError, TypeError):
            return ValidationError("Selecciona un dia valido.")
        dias = list(Dia.objects.filter(pk__in=ids).order_by("id"))
        if len(dias) != len(ids):
            return ValidationError("Selecciona un dia valido.")
        return dias

    def _clean_schedule_time(self, value, label):
        if not value:
            return ValidationError("Este campo es obligatorio.")
        field = forms.TimeField(input_formats=("%H:%M",))
        try:
            return field.clean(value)
        except ValidationError:
            return ValidationError(f"{label} debe tener formato HH:MM.")

    def _has_schedule_overlap(self, rows):
        grouped_rows = {}
        for row in rows:
            grouped_rows.setdefault(row["dia_actividad"].id, []).append(row)

        for day_rows in grouped_rows.values():
            ordered_rows = sorted(day_rows, key=lambda row: row["hora_inicio"])
            for index in range(1, len(ordered_rows)):
                if (
                    ordered_rows[index]["hora_inicio"]
                    < ordered_rows[index - 1]["hora_fin"]
                ):
                    return True
        return False

    def _has_existing_schedule_overlap(self, rows, catalogo_actividad):
        for row in rows:
            overlapping = ActividadEspacioPWA.objects.filter(
                comedor=self.comedor,
                dia_actividad=row["dia_actividad"],
                catalogo_actividad=catalogo_actividad,
                activo=True,
                hora_inicio__lt=row["hora_fin"],
                hora_fin__gt=row["hora_inicio"],
            )
            if self.instance and self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                return True
        return False

    def get_schedule_data(self):
        return list(self._schedule_data)

    @property
    def schedule_form_rows(self):
        rows = []
        for index, row in enumerate(self.schedule_rows):
            errors = (
                self.schedule_errors[index] if index < len(self.schedule_errors) else {}
            )
            rows.append({"key": row["key"], "values": row, "errors": errors})
        return rows

    def get_service_data(self, schedule):
        data = dict(self.cleaned_data)
        data.pop("categoria", None)
        data.update(schedule)
        data["horario_actividad"] = _format_activity_schedule(
            data.get("hora_inicio"),
            data.get("hora_fin"),
        )
        return data
