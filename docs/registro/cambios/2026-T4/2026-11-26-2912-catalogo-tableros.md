# Cambio: sincronización conservadora del catálogo de tableros (#2912)

## Alcance

El catálogo de código pasa de `dashboard/fixtures/tableros.json` a `dashboard/catalogo/tableros.json`. Se sincroniza mediante el callback posterior a `load_fixtures`. El cargador general conserva su contrato; el archivo de tableros ya no se descubre como fixture ni se sobrescribe por PK con `--force`.

## Comportamiento

La sincronización identifica entradas existentes por la combinación de PK y slug. Conserva nombre, estado, permisos y otros campos operativos; actualiza únicamente URL o ruta interna cuando están presentes en el catálogo. Las entradas nuevas usan los valores del catálogo y, si no se especifica estado, el valor predeterminado activo. No se eliminan entradas ausentes.

Una colisión o identidad inválida revierte todo el lote e informa que el catálogo no se sincronizó, sin detener la carga general. El aviso requiere investigación antes de depender de la actualización del catálogo. No incluye URLs ni valores de la entrada.

## Verificación

Pruebas sintéticas cubren idempotencia, preservación, creación, colisión y rollback, y carga normal y forzada mediante recorrido y registro reales. Gitleaks localizado y pylint ejecutados en Docker. No se consultaron datos reales.

## Limitaciones

Una versión anterior del migrador que aún contenga el fixture antiguo puede sobrescribir campos durante un despliegue mixto; coordinar la secuencia y verificar la versión antes de activar el cambio. Las URLs pueden ser sensibles y se debe revisar la política de auditoría actual; no se incluyen en el aviso. Esta unidad no concede acceso ni implementa audiencias o alcance de datos. No se hizo publicación ni despliegue.
