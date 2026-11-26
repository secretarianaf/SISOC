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

Los archivos `sisoc-produccion.conf` y `sisoc-qa.conf` son candidatos de referencia, no prueba del estado efectivo ni autorizacion para instalarlos. Produccion conserva el contrato suministrado; QA conserva la referencia suministrada. HML tiene un candidato basado en producción; sus rutas, TLS y topología requieren comparación por Infra con hml-old antes de activarlo.

Antes de incorporar un entorno, Infra debe comparar el vhost y el snippet PWA efectivos con los candidatos y conservar toda ruta, proteccion y dependencia vigente. El archivo `sisoc-pwas.conf` del repositorio no acredita el contenido activo en ningun entorno. Las zonas `default` y `sisoc_admin` de produccion y los certificados son dependencias externas, no se crean aqui.

La regla existente para `/media/cdi/` en la referencia de produccion no debe activarse sin completar la remediacion y verificacion documentadas en [comandos de administracion](../comandos_administracion.md). No cerrar `/media/documentacion/`; sigue siendo utilizada por Comedores. La proteccion de CDF se refiere a `/media/centrodefamilia/cargas_masivas/` y no debe confundirse con otras rutas de CDF.

Para probar sin hosts reales: `python src/backends/kernel/tests/test_nginx_docker_contract.py`. El test genera certificados temporales y usa contenedores sin red con archivos sinteticos; no acredita el estado de ningun servidor.

## Marcador del paquete cargado (diseño T2a)

Los candidatos de QA y PRD incluyen `/etc/nginx/snippets/sisoc-package-marker.conf` exclusivamente dentro del bloqueo CDF. El include debe existir antes de instalar cualquiera de los candidatos; si falta, `nginx -t` falla. Su futura generacion e instalacion atomica pertenecen a T2b y no estan implementadas por este cambio. Hasta entonces estas referencias no estan listas para activarse en ningun servidor.

Infra deberá mantener el include y su directorio fuera del control del runner, con propietario root y sin escritura por terceros. El contenido futuro debe limitarse a una directiva `add_header X-SISOC-Nginx-Package "<identidad-del-paquete-aprobado>" always;`, derivada de los archivos aprobados sin incluir el propio marcador en su calculo. La identidad no es un secreto ni constituye una firma. No aceptar el texto de la directiva ni la identidad como autoridad del runner.

El marcador solo aporta evidencia de la generacion atendida por el vhost cuando el helper, todavia pendiente, verifique ademas procedencia, archivos y alcance. La prueba usa 404 CDF por loopback, sin proxy, con Host y SNI correctos y comprobacion TLS en PRD; preservar HSTS requiere declararlo tambien en ese `location`, porque `add_header` cambia su herencia. El test demuestra que editar el include en disco cambia `nginx -T`, pero no cambia el marcador servido hasta recargar.

El diseño de incorporación, permisos y rollback está en [reconciliación de Nginx](reconciliacion.md).
