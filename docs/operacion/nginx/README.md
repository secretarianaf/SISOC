# Nginx de SISOC

`sisoc-produccion.conf` es la referencia del vhost de producción.

## La cadena TLS tiene que estar completa

`ssl_certificate` apunta a `fullchain.crt`, que debe contener **el certificado
del sitio y el intermedio**, en ese orden. Si sólo tiene el de hoja, los
navegadores y `curl` igual funcionan —completan la cadena por AIA— pero
**Android no lo hace**: las apps móviles fallan con un `Network Error` genérico
en todas las requests, sin ninguna pista de la causa.

Ya pasó dos veces: al equipo de SISOC - Mobile (comedores) le llevó días
diagnosticarlo, y volvió a aparecer con DataCalle en septiembre de 2026.

**Verificación** (tiene que dar **2**, no 1):

```bash
openssl s_client -connect sisoc.secretarianaf.gob.ar:443 \
  -servername sisoc.secretarianaf.gob.ar </dev/null 2>/dev/null \
  | grep -c "BEGIN CERTIFICATE"
```

Y la validación completa no debe dar error:

```bash
openssl s_client -connect sisoc.secretarianaf.gob.ar:443 \
  -servername sisoc.secretarianaf.gob.ar </dev/null 2>&1 \
  | grep "Verify return code"
# esperado: Verify return code: 0 (ok)
# síntoma:  Verify return code: 21 (unable to verify the first certificate)
```

**Arreglo**: concatenar el intermedio de la CA al certificado del sitio y
recargar nginx.

```bash
cat sitio.crt intermedio.crt > /etc/apache2/certs/fullchain.crt
nginx -t && systemctl reload nginx
```

El intermedio actual es **Sectigo Public Server Authentication CA DV R36**.
Conviene repetir la verificación después de cada renovación del certificado:
es el momento en el que se vuelve a perder.

# Referencias Nginx por entorno

Los archivos `sisoc-produccion.conf` y `sisoc-qa.conf` son candidatos de referencia, no prueba del estado efectivo ni autorizacion para instalarlos. Produccion conserva el contrato suministrado; QA conserva la referencia suministrada. HML requiere relevamiento por Infra, sin suposiciones sobre sus rutas, TLS o topologia.

Antes de incorporar un entorno, Infra debe comparar el vhost y el snippet PWA efectivos con los candidatos y conservar toda ruta, proteccion y dependencia vigente. El archivo `sisoc-pwas.conf` del repositorio no acredita el contenido activo en ningun entorno. Las zonas `default` y `sisoc_admin` de produccion y los certificados son dependencias externas, no se crean aqui.

La regla existente para `/media/cdi/` en la referencia de produccion no debe activarse sin completar la remediacion y verificacion documentadas en [comandos de administracion](../comandos_administracion.md). No cerrar `/media/documentacion/`; sigue siendo utilizada por Comedores. La proteccion de CDF se refiere a `/media/centrodefamilia/cargas_masivas/` y no debe confundirse con otras rutas de CDF.

Para probar sin hosts reales: `python src/backends/kernel/tests/test_nginx_docker_contract.py`. El test genera certificados temporales y usa contenedores sin red con archivos sinteticos; no acredita el estado de ningun servidor.
