# Cambio: evaluación local de requisitos web (#2785, F1a)

## Alcance

Primera unidad de la implementación local autorizada de INS-A. Se incorpora
`src/backends/sisoc_core/usuarios/web_session.py` y su prueba pública en
`src/backends/sisoc_core/tests/test_web_session_readiness.py`.
El seguimiento original corresponde al worktree piloto de INS-A; este registro
conserva su evidencia histórica al separar la misma unidad en el worktree actual.

## Comportamiento

`resolve_web_access(request)` devuelve el primer requisito pendiente, sin escribir
datos: sesión activa, acceso web, cambio de contraseña, confirmación de perfil,
encuesta obligatoria y finalmente `ready`. Conserva los helpers existentes de
perfiles y el servicio de rondas pendientes, con el mismo criterio de
obligatoriedad. Un perfil ausente se rechaza; no se crea para permitir acceso.
No consulta encuestas tras un rechazo anterior y propaga fallos de dependencia
en lugar de afirmar que la sesión está lista.

No se publica todavía un endpoint, ni se cambian middleware globales, permisos,
login/token PWA, frontend, modelos, dependencias o #2789. El resultado no autoriza
una operación de negocio: cada futura API debe comprobar sesión, requisitos,
permiso propio, CSRF y alcance del objeto por petición.

## Verificación

- RED observado: el test nuevo falló al importar `usuarios.web_session`, antes de
  crear la implementación. Dos intentos previos con Python global fallaron por
  dependencias de entorno; no se contabilizan como RED de comportamiento.
- GREEN: 16 pruebas del resolver, cobertura del módulo 100%.
- Regresión: 89 pruebas existentes de autenticación, identidad y middleware de
  encuestas aprobadas; sin cambios en sus fuentes.
- Verificación independiente: 16 pruebas del candidato y seis probes adicionales
  en copia temporal, con bloqueo de DB y estado de modelos sin cambios. Sin
  bloqueantes. Los probes no encontraron una regresión que requiera test nuevo.
- Black check: ambos archivos conformes. Pylint del módulo: 10/10.
- Ejecución en imagen local `a8e59c769a92`, paquetes principales contrastados con
  los requisitos versionados. Contenedores efímeros, sin red, `env -i`, repositorio
  readonly, dotenv deshabilitado, SQLite de tests y logs/media/cache temporales.
- Advertencias existentes: próximo cambio de URLField en Django 6 y HarfBuzz
  para WeasyPrint. No se modifican dependencias para silenciarlas.

Comando focal dentro de ese aislamiento:

```text
python -m pytest src/backends/sisoc_core/tests/test_web_session_readiness.py -q --create-db -o addopts= -o cache_dir=/scratch/cache --basetemp=/scratch/pytest --cov=usuarios.web_session --cov-report=term-missing --cov-fail-under=80
```

## Limitaciones y retorno

F1b/contexto HTTP, navegación, entorno visual, React y el circuito INS-A siguen
pendientes. No se ejecutaron diffs visuales ni se obtuvo aceptación humana;
esta unidad no modifica pantallas. CI, revisión nativa, publicación y despliegue
son estados separados y no se afirman por estas comprobaciones locales.
El helper todavía no tiene consumidores de producción; retirar esta unidad
consiste en retirar su módulo y tests, no revertir datos ni middleware.

Riesgo: item 2, requisito previo de autorización. Requiere revisión técnica.
