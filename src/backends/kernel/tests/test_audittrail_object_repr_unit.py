"""Audit object labels must not bypass sensitive field allowlists (#2791)."""

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_save


@pytest.mark.parametrize(
    "app_label,model,label",
    [
        ("celiaquia", "expedienteciudadano", "Legajo Celiaquía"),
        ("ver_para_ser_libre", "registronominalvpsl", "Registro nominal VPSL"),
        ("ver_para_ser_libre", "casolaboratoriovpsl", "Caso de laboratorio VPSL"),
    ],
)
def test_sensitive_audit_labels_only_contain_model_and_identifier(
    app_label, model, label
):
    entry = LogEntry(
        content_type=ContentType(app_label=app_label, model=model),
        object_pk="123",
        object_repr="45111222 - Nombre Apellido",
        changes={"estado": ["cargado", "validado"]},
    )

    pre_save.send(sender=LogEntry, instance=entry, raw=False)

    assert entry.object_repr == f"{label} #123"
    assert entry.object_pk == "123"
    assert entry.changes == {"estado": ["cargado", "validado"]}


def test_existing_audit_labels_keep_their_previous_representation():
    entry = LogEntry(
        content_type=ContentType(app_label="comedores", model="comedor"),
        object_pk="123",
        object_repr="Existing institutional label",
    )

    pre_save.send(sender=LogEntry, instance=entry, raw=False)

    assert entry.object_repr == "Existing institutional label"
