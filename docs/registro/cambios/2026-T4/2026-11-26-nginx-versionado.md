> Histórico: la automatización de reconciliación de Nginx fue retirada; no usar este documento como procedimiento vigente.

# Cambio: referencias y reconciliación de Nginx

## Alcance

Se versionan referencias de QA, producción y HML basado en producción y se agrega un mecanismo de reconciliación propuesto para los tres despliegues. HML requiere comparar y aprobar su candidato y definir datos de probe por Infra antes de su incorporación; no se afirma que el candidato coincida con el servidor real. Ningún entorno se incorpora automáticamente por este cambio.

## Comportamiento

Un entorno sin incorporación se informa como no gestionado. Un entorno habilitado exige que un helper preinstalado por Infra acredite los bytes del paquete frente a un manifiesto root-owned por entorno. Ante cambios aprobados, respalda archivos, instala, valida, recarga y comprueba el marcador mediante socket root-only y el 404 público; ante error intenta restaurar y falla el despliegue. La reversión de la aplicación no revierte Nginx. Los permisos, precondiciones de CDI, recuperación y límites se describen en referencia histórica de reconciliación de Nginx.

## Verificación

Se ejecutaron pruebas de contrato y de integración local con Nginx real en Docker sin red; `systemctl` y los datos son sintéticos. La verificación independiente evaluó aislamiento del socket, manifiestos y rollback ante escritura intermedia. Estas pruebas no acreditan permisos, PWA, certificado o configuración efectiva de ningún servidor. Antes de activar se debe comprobar que el runner y el backend no tengan control equivalente a root mediante Docker; de otro modo la frontera root-only no protege al host.

## Cotejo de HML

Una inspección SSH autorizada, sin sudo y sin cambios, observó las rutas `/MID/`, alias com.hml y PWA de Inspecciones; se preservan en el candidato y en su snippet propio. El runner `sisoc-deploy` pertenece al grupo con acceso al socket de Docker y el daemon corre como root; no se comprobó una política externa de autorización. La independencia del helper debe resolverse antes de activar. La inspección no demuestra la configuración completamente cargada ni probó datos privados.
