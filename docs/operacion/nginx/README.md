# Referencias Nginx por entorno

Los archivos `sisoc-produccion.conf` y `sisoc-qa.conf` son candidatos de referencia, no prueba del estado efectivo ni autorizacion para instalarlos. Produccion conserva el contrato suministrado; QA conserva la referencia suministrada. HML requiere relevamiento por Infra, sin suposiciones sobre sus rutas, TLS o topologia.

Antes de incorporar un entorno, Infra debe comparar el vhost y el snippet PWA efectivos con los candidatos y conservar toda ruta, proteccion y dependencia vigente. El archivo `sisoc-pwas.conf` del repositorio no acredita el contenido activo en ningun entorno. Las zonas `default` y `sisoc_admin` de produccion y los certificados son dependencias externas, no se crean aqui.

La regla existente para `/media/cdi/` en la referencia de produccion no debe activarse sin completar la remediacion y verificacion documentadas en [comandos de administracion](../comandos_administracion.md). No cerrar `/media/documentacion/`; sigue siendo utilizada por Comedores. La proteccion de CDF se refiere a `/media/centrodefamilia/cargas_masivas/` y no debe confundirse con otras rutas de CDF.

Para probar sin hosts reales: `python src/backends/kernel/tests/test_nginx_docker_contract.py`. El test genera certificados temporales y usa contenedores sin red con archivos sinteticos; no acredita el estado de ningun servidor.
