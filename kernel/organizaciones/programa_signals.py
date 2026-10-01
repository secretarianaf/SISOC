"""``Programa.organismo_id`` vuelve a NULL cuando se borra su organización.

Reemplaza el ``on_delete=SET_NULL`` de la antigua FK ``core.Programa.organismo``:
el kernel guarda solo el id para no depender de ``organizaciones``, y la FK
física sigue en la DB, así que sin esto el borrado fallaría por integridad.
"""

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from core.models import Programa
from organizaciones.models import Organizacion


@receiver(pre_delete, sender=Organizacion)
def desvincular_programas(sender, instance, **kwargs):
    del sender, kwargs
    Programa.objects.filter(organismo_id=instance.pk).update(organismo_id=None)
