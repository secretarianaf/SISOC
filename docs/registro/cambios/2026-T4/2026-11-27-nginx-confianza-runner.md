> Histórico: la automatización de reconciliación de Nginx fue retirada; no usar este documento como procedimiento vigente.

# Cambio: confianza en el runner para Nginx gestionado

## Alcance

El usuario aceptó confiar en el runner actual con acceso a Docker rootful. El gate advierte sobre el socket local escribible en lugar de bloquear por ese único motivo. No se cambia la aprobación de paquetes, los destinos, el lock, la validación, la recarga ni el rollback del helper.

## Comportamiento y riesgo

Un runner comprometido puede modificar el host, omitir el gate y alterar las aprobaciones. El manifiesto root-owned y el socket privado no constituyen una frontera frente a él. La aceptación del riesgo no activa Nginx ni autoriza cambios en los servidores; Infra debe completar las precondiciones del runbook histórico de reconciliación de Nginx.

En QA, el candidato bloquea rutas de CDF e Inspecciones; antes de activarlo debe verificarse su impacto sin consultar archivos privados. Un rollback de la aplicación no retira automáticamente la protección Nginx; el rollback del helper requiere validación operativa y puede requerir intervención si falla o hay interrupción abrupta.

## Verificación

El test aislado del gate comprueba que un socket Docker escribible produce advertencia y envía el paquete al wrapper, y conserva las comprobaciones de estados incompletos. Las pruebas locales no demuestran aislamiento, estado real de servidores ni aceptación humana. La activación y el deploy siguen pendientes.
