# Selectores con búsqueda: dependencia legacy o comportamiento React

Estado **E2, J2 elegida explícitamente por el responsable («j2»)**. No instalar paquetes, modificar scripts,
inicializar plugins ni cambiar formularios. Diseño idéntico y comparación visual
por URL/estado siguen vigentes en ambas alternativas.

## Necesidad concreta y práctica existente

Fuente congelada `59a8f797688c9e762d5a4e9eaa187698ffade8aa`, coincidente con los
archivos comparados del checkout:

| Fuente | Hallazgo que condiciona el plan |
|---|---|
| `src/backends/kernel/templates/scripts/mainscripts.html` | Carga jQuery 3.6.0 y Select2 4.1.0-beta.1 desde recursos externos; cargar todo ese archivo también arrastra otros plugins. No trasladarlo entero al index React |
| `src/backends/kernel/static/custom/js/custom.js` | Inicializa y detecta select2 sobre select.select2; hay ciclo de inicialización que no se replica con solo un select nativo |
| `src/backends/cdf/centrodefamilia/forms.py` | ActividadCentroForm usa SelectMultiple con select2 para sexoact y dias: valores múltiples y etiquetas/opciones propias |
| `src/backends/inspecciones/inspecciones/templates/inspecciones/partials/asignacion_form.html` | Selectores remotos de inspector/escuela, selección inicial, mínimo tres caracteres y ayudas/límites. No equivalen a descargar todas las opciones y filtrar en navegador |
| `src/frontends/apps/vpsl/src/Workflow.tsx` | Ya hay formulario React con Autocomplete de MUI y estado React, sin Select2 en ese componente. Es patrón de selección, no equivalencia probada del aspecto o de búsqueda remota |
| `src/frontends/packages/ui/package.json` | React y MUI ya declarados en paquetes del monorepo; no se necesita elegir otra biblioteca para comenzar a definir selectores |

Se inspeccionó la práctica existente antes de proponer un mecanismo nuevo.
No se ejecutó el plugin ni el componente, no se midieron tiempos y no se
declaró paridad. La búsqueda inicial de editores no justifica migrar Summernote
por aparecer en un script global: exigir consumidor real antes de agregar trabajo.

«Toda la aplicación React, sin formularios Django» ya está confirmado. Un
componente React puede encapsular un plugin imperativo sin conservar templates
Django, pero eso mantiene dependencia/ciclo de vida jQuery en la interfaz nueva.
La elección no quedó resuelta por M2 ni por preservar CSS/imagenes actuales.

Ver [decisión registrada](../../registro/decisiones/2026-10-27-2787-selectores-react-j2.md).

## Alternativas evaluadas: J2 elegida, J1 descartada

| Opción | Implementación futura de selectores | Ganancia | Costo / consecuencia |
|---|---|---|---|
| J1. Encapsular Select2 actual | React es dueño del formulario y payload; un componente local integra el plugin actual sobre un nodo aislado, sincroniza cambios y destruye instancia al desmontar | Reutiliza implementación/apariencia del selector origen, reduciendo la reescritura de su interacción | Mantiene jQuery/Select2 como dependencias de los nuevos circuitos React; cuidado con doble estado, listeners, foco, modales y montaje repetido. No autoriza copiar todos los scripts globales ni actualizarlos |
| J2. Selectores con comportamiento React | Usar el patrón React existente donde encaje, conservando estilos y semántica del selector actual; adaptar búsquedas remotas/múltiples y payload por control | Evita trasladar jQuery/Select2 a los circuitos migrados y mantiene estado/ciclo de vida en React | Hay que reproducir interacción, foco/teclado, opciones iniciales, paginación/búsqueda y apariencia; requiere pruebas/diff específicos. El componente MUI por defecto no cumple automáticamente la identidad visual |

**Recomendación del agente: J2**, alineada con el destino React y los patrones ya
presentes. Empezar con componentes locales, sin motor universal ni paquete nuevo;
extraer a compartido solo cuando haya reutilización concreta y regresión cubierta.
No promete que el reemplazo sea trivial o que conserve apariencia sin validarlo.

J1 queda descartada por la elección explícita de J2. Ambas alternativas evaluadas conservan
backend/Form como autoridad y el mismo diseño; J2 no autoriza rediseño MUI.
No se elige plugin/biblioteca nueva ni se evalúan licencias/precios por suposición.

## Criterios de aceptación comunes

- Single/multiple, selección vacía, valores iniciales, valores actuales inactivos,
  cambio de padre que invalida hijo y envío de valores repetidos según Form.
- Búsqueda remota con mismo mínimo, filtros/permisos, orden, paginación/límite y
  selección inicial aunque no esté en la página de resultados. Evitar respuestas
  antiguas que sustituyan una selección reciente; no inventar cache persistente.
- Opciones autorizadas por backend, validación de IDs/rangos/relación repetida
  en submit. No cargar catálogos completos ni ampliar ámbito por comodidad de UI.
- Comparar control cerrado, abierto, escribiendo, sin resultados, cargando,
  error, multiselección y validación; teclado, foco, ESC, scroll, modal y móvil.
- Mantener altura, tipografía, bordes, chips, iconos, ayudas, mensajes y ancho;
  ninguna diferencia inesperada se acepta por cambiar de librería.
- Montaje/desmontaje y navegación repetidos, sin handlers duplicados o listeners
  globales que alteren otros controles. Con J1, un único dueño del subárbol DOM.
- No ampliar el cambio a Celiaquía/VPSL/INET o paquetes compartidos sin evidencia
  y alcance explícitos; admin/Unfold queda aparte.

J2 resuelve el enfoque de estos selectores. Los
[contratos concretos](2026-10-27-2787-selectores-contratos-j2.md) y su manifiesto
precisan valores, búsqueda y dependencias. Implementación y evidencia siguen
pendientes; no se trasladan automáticamente decisiones a otros plugins.
