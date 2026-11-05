from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def monto(valor):
    """Formato de montos del legajo: ``$100.000.000`` (centavos solo si hay)."""
    if valor is None or valor == "":
        return ""
    try:
        numero = Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return valor
    signo = "-" if numero < 0 else ""
    entero, centavos = f"{abs(numero):.2f}".split(".")
    miles = f"{int(entero):,}".replace(",", ".")
    if centavos == "00":
        return f"{signo}${miles}"
    return f"{signo}${miles},{centavos}"
