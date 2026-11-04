/**
 * EDITOR DINÁMICO DE PREGUNTAS - ENCUESTAS
 *
 * No usa formsets de Django: arma un array de preguntas en el cliente
 * (clonando #pregunta-row-template, mismo patrón que advanced_filters.js) y lo
 * serializa como JSON en el input oculto #preguntas_json justo antes de
 * enviar el formulario. El backend valida y parsea ese JSON en
 * encuestas/validators.py (parse_preguntas_payload).
 */
(function () {
    "use strict";

    var container = document.getElementById("preguntas-container");
    var template = document.getElementById("pregunta-row-template");
    var addBtn = document.getElementById("agregar-pregunta");
    var hiddenInput = document.getElementById("preguntas_json");
    var vacioMsg = document.getElementById("preguntas-vacio-msg");
    var cantidadEl = document.getElementById("preguntas-cantidad");
    var form = document.getElementById("encuesta-form");
    var contextEl = document.querySelector("[data-tipos-con-opciones]");
    var initialDataEl = document.getElementById("preguntas-iniciales");
    var filaArrastrada = null;
    var destinoArrastre = null;
    var modalQuitarEl = document.getElementById("quitar-pregunta-modal");
    var advertenciaQuitarEl = document.getElementById("quitar-pregunta-advertencia");
    var confirmarQuitarBtn = document.getElementById("confirmar-quitar-pregunta");
    var cancelarQuitarBtn = document.getElementById("cancelar-quitar-pregunta");
    var filaPorQuitar = null;
    var scrollArrastreTimer = null;
    var velocidadScrollArrastre = 0;

    if (!container || !template || !addBtn || !hiddenInput || !form) {
        return;
    }

    function detenerScrollArrastre() {
        if (scrollArrastreTimer !== null) window.clearInterval(scrollArrastreTimer);
        scrollArrastreTimer = null;
        velocidadScrollArrastre = 0;
    }

    document.addEventListener("dragover", function (event) {
        if (!filaArrastrada) return;
        event.preventDefault();
        var margen = Math.min(100, window.innerHeight / 4);
        var distancia = event.clientY < margen ? event.clientY - margen
            : event.clientY > window.innerHeight - margen ? event.clientY - window.innerHeight + margen : 0;
        if (!distancia || event.clientX < 0 || event.clientX > window.innerWidth) {
            detenerScrollArrastre();
            return;
        }
        velocidadScrollArrastre = Math.max(-18, Math.min(18, distancia / margen * 18));
        if (scrollArrastreTimer === null) {
            scrollArrastreTimer = window.setInterval(function () {
                if (!filaArrastrada) {
                    detenerScrollArrastre();
                    return;
                }
                window.scrollBy({ top: velocidadScrollArrastre, left: 0, behavior: "instant" });
            }, 16);
        }
    });
    document.addEventListener("drop", function (event) {
        detenerScrollArrastre();
        if (filaArrastrada && destinoArrastre && container.contains(event.target)) {
            event.preventDefault();
            soltarFila(destinoArrastre);
        }
        limpiarDestinoArrastre();
    });
    document.addEventListener("dragend", detenerScrollArrastre);
    document.addEventListener("dragleave", function (event) {
        if (!event.relatedTarget) detenerScrollArrastre();
    });

    var modalQuitar = bootstrap.Modal.getOrCreateInstance(modalQuitarEl);
    modalQuitarEl.addEventListener("shown.bs.modal", function () {
        cancelarQuitarBtn.focus();
    });
    modalQuitarEl.addEventListener("hidden.bs.modal", function () {
        if (filaPorQuitar && container.contains(filaPorQuitar)) {
            filaPorQuitar._preguntaRefs.quitarBtn.focus();
        } else {
            var primera = container.children[0];
            (primera ? primera._preguntaRefs.arrastrar : addBtn).focus();
        }
        filaPorQuitar = null;
    });
    confirmarQuitarBtn.addEventListener("click", function () {
        if (!filaPorQuitar || !container.contains(filaPorQuitar)) return;
        filaPorQuitar.remove();
        actualizarVacioMsg();
        renumerarFilas();
        modalQuitar.hide();
    });

    var tiposConOpciones = (contextEl ? contextEl.getAttribute("data-tipos-con-opciones") : "")
        .split(",")
        .map(function (tipo) { return tipo.trim(); })
        .filter(Boolean);

    // Tipos que pueden ponderar para el puntaje total (ver Pregunta.pondera
    // en encuestas/models.py): Sí/No, opción única/múltiple y escala tienen
    // un conjunto fijo de valores posibles. Texto libre, numérico y fecha no
    // muestran el toggle de puntaje.
    var tiposPonderables = (contextEl ? contextEl.getAttribute("data-tipos-ponderables") : "")
        .split(",")
        .map(function (tipo) { return tipo.trim(); })
        .filter(Boolean);

    // Si/No y las preguntas de opción (única o múltiple) tienen un conjunto
    // fijo y conocido de valores posibles: para esas, "Valor esperado" se
    // arma con un <select> en vez de texto libre, para no depender de que
    // alguien escriba exactamente "si"/"Sí"/"SI" (motivo real de un bug: la
    // condición nunca coincidía porque el value real que viaja en el POST es
    // "si" en minúscula, ver campo_pregunta.html).
    var OPCIONES_SI_NO = [["si", "Sí"], ["no", "No"]];

    function actualizarVacioMsg() {
        var hayFilas = container.children.length > 0;
        if (vacioMsg) vacioMsg.classList.toggle("d-none", hayFilas);
        if (cantidadEl) cantidadEl.textContent = String(container.children.length);
    }

    /** Renumera badges y refresca las opciones de "mostrar si" de cada fila
     * para que cada una solo pueda referenciar preguntas anteriores. */
    function renumerarFilas() {
        var filas = Array.from(container.children);
        filas.forEach(function (fila, indice) {
            var refs = fila._preguntaRefs;
            if (!refs) return;
            refs.numero.textContent = "Pregunta " + (indice + 1);
            refs.quitarBtn.classList.toggle("d-none", false);

            refs.condicionRef.innerHTML = "";
            refs.condicionRef.appendChild(crearOption("", "(siempre visible)"));
            filas.slice(0, indice).forEach(function (filaAnterior) {
                var refsAnterior = filaAnterior._preguntaRefs;
                var texto = refsAnterior.texto.value.trim() || ("Pregunta " + (filas.indexOf(filaAnterior) + 1));
                refs.condicionRef.appendChild(crearOption(String(filas.indexOf(filaAnterior) + 1), texto));
            });
            var referencia = filas.indexOf(refs._condicionFila);
            refs.condicionRef.value = referencia >= 0 && referencia < indice ? String(referencia + 1) : "";
            if (!refs.condicionRef.value) refs._condicionFila = null;
            var condicionDisponible = indice > 0;
            refs.condicionWrap.classList.toggle("d-none", !condicionDisponible);
            if (!condicionDisponible) {
                refs.condicionRef.value = "";
            }
        });
        refrescarCondicionesValor();
    }

    function anunciarOrden(mensaje, tipo) {
        toastr[tipo || "success"](mensaje, null, {
            positionClass: "toast-bottom-right",
            timeOut: 3000,
            extendedTimeOut: 0,
            hideDuration: 0,
            escapeHtml: true,
        });
    }

    function limpiarDestinoArrastre() {
        destinoArrastre = null;
        Array.from(container.children).forEach(function (fila) {
            fila.classList.remove("pregunta-destino-antes", "pregunta-destino-despues");
        });
    }

    function soltarFila(destino) {
        var indice = Array.from(container.children).indexOf(destino);
        // Quitar el espacio antes de medir las posiciones de la animación final.
        limpiarDestinoArrastre();
        moverFila(filaArrastrada, indice);
    }

    function moverFila(fila, destino) {
        var filas = Array.from(container.children);
        var origen = filas.indexOf(fila);
        if (origen < 0 || destino < 0 || destino >= filas.length || origen === destino) return;
        filas.splice(origen, 1);
        filas.splice(destino, 0, fila);
        var invalido = filas.some(function (actual, indice) {
            var referencia = actual._preguntaRefs._condicionFila;
            return referencia && filas.indexOf(referencia) >= indice;
        });
        if (invalido) {
            anunciarOrden("No se puede mover: una pregunta condicional debe quedar después de la pregunta de la que depende.", "warning");
            return;
        }
        var scrollX = window.scrollX;
        var scrollY = window.scrollY;
        var posiciones = filas.map(function (actual) { return actual.getBoundingClientRect().top; });
        // Mover solo la tarjeta elegida evita desmontar todo el listado y perder el anclaje del scroll.
        container.insertBefore(fila, filas[destino + 1] || null);
        renumerarFilas();
        anunciarOrden("Pregunta movida a la posición " + (destino + 1) + ". Guardá la encuesta para conservar el orden.");
        if (window.scrollX !== scrollX || window.scrollY !== scrollY) {
            window.scrollTo({ left: scrollX, top: scrollY, behavior: "instant" });
        }
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            filas.forEach(function (actual, indice) {
                var desplazamiento = posiciones[indice] - actual.getBoundingClientRect().top;
                if (desplazamiento && actual.animate) {
                    actual.animate([
                        { transform: "translateY(" + desplazamiento + "px)" },
                        { transform: "translateY(0)" },
                    ], { duration: 180, easing: "ease-out" });
                }
            });
        }
    }

    /** Devuelve las opciones [valor, etiqueta] disponibles para la condición
     * según el tipo de la pregunta referenciada, o null si ese tipo no tiene
     * un conjunto fijo (texto/número/fecha siguen siendo texto libre). */
    function opcionesCondicionParaFila(filaReferencia) {
        var refsRef = filaReferencia._preguntaRefs;
        if (refsRef.tipo.value === "si_no") return OPCIONES_SI_NO;
        if (tiposConOpciones.indexOf(refsRef.tipo.value) !== -1) {
            return refsRef.opciones.value
                .split("\n")
                .map(function (linea) { return linea.trim(); })
                .filter(Boolean)
                .map(function (linea) { return [linea, linea]; });
        }
        return null;
    }

    function leerValorCondicionActivo(refs) {
        if (!refs.condicionValorSelect.classList.contains("d-none")) {
            return refs.condicionValorSelect.value;
        }
        return refs.condicionValor.value;
    }

    function escribirValorCondicionActivo(refs, valor) {
        if (!refs.condicionValorSelect.classList.contains("d-none")) {
            refs.condicionValorSelect.value = valor;
        } else {
            refs.condicionValor.value = valor;
        }
    }

    /** Muestra el <select> de valores fijos (y lo repuebla) o el <input> de
     * texto libre, según el tipo de la pregunta que esta fila referencia. */
    function actualizarValorCondicion(refs) {
        var ordenRef = parseInt(refs.condicionRef.value, 10);
        var filaReferencia = ordenRef ? container.children[ordenRef - 1] : null;
        var opciones = filaReferencia ? opcionesCondicionParaFila(filaReferencia) : null;

        if (!opciones) {
            refs.condicionValorSelect.classList.add("d-none");
            refs.condicionValorSelect.innerHTML = "";
            refs.condicionValor.classList.remove("d-none");
            return;
        }

        var valorPrevio = leerValorCondicionActivo(refs);
        refs.condicionValorSelect.innerHTML = "";
        opciones.forEach(function (par) {
            refs.condicionValorSelect.appendChild(crearOption(par[0], par[1]));
        });
        if (opciones.some(function (par) { return par[0] === valorPrevio; })) {
            refs.condicionValorSelect.value = valorPrevio;
        }
        refs.condicionValor.classList.add("d-none");
        refs.condicionValorSelect.classList.remove("d-none");
    }

    function refrescarCondicionesValor() {
        Array.from(container.children).forEach(function (fila) {
            actualizarValorCondicion(fila._preguntaRefs);
        });
    }

    function crearOption(value, label) {
        var option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
    }

    function actualizarVisibilidadOpciones(refs) {
        var requiereOpciones = tiposConOpciones.indexOf(refs.tipo.value) !== -1;
        refs.opcionesWrap.classList.toggle("d-none", !requiereOpciones);
        var esTexto = refs.tipo.value === "texto_corto" || refs.tipo.value === "texto_largo";
        refs.maxCaracteresWrap.classList.toggle("d-none", !esTexto);
        if (!esTexto) refs.maxCaracteres.value = "";
    }

    /** Renueva las filas de "puntaje por opción" a partir de las líneas
     * actuales del textarea de opciones, conservando el puntaje ya cargado
     * por texto de opción (no por posición: reordenar o agregar una línea
     * en el medio no desarma los puntajes ya cargados de las demás). */
    function actualizarFilasPuntajeOpciones(refs) {
        var textos = refs.opciones.value
            .split("\n")
            .map(function (linea) { return linea.trim(); })
            .filter(Boolean);

        refs.puntajeOpcionesList.innerHTML = "";
        textos.forEach(function (texto) {
            var fila = document.createElement("div");
            fila.className = "puntaje-opcion-row";

            var label = document.createElement("span");
            label.className = "puntaje-opcion-texto";
            label.textContent = texto;
            label.title = texto;

            var input = document.createElement("input");
            input.type = "number";
            input.min = "0";
            input.className = "form-control puntaje-opcion-input";
            input.value = Object.prototype.hasOwnProperty.call(refs._puntajesPorOpcion, texto)
                ? refs._puntajesPorOpcion[texto]
                : 0;
            input.addEventListener("input", function () {
                refs._puntajesPorOpcion[texto] = input.value;
            });

            fila.appendChild(label);
            fila.appendChild(input);
            refs.puntajeOpcionesList.appendChild(fila);
        });
    }

    /** Muestra los campos de puntaje que correspondan según el tipo de
     * pregunta, solo si el switch "¿Pondera?" está activo. */
    function actualizarDetallePondera(refs) {
        var activo = refs.pondera.checked;
        refs.ponderaDetalle.classList.toggle("d-none", !activo);
        refs.puntajeSiNoWrap.classList.add("d-none");
        refs.puntajeOpcionesWrap.classList.add("d-none");
        refs.puntajeEscalaNota.classList.add("d-none");
        if (!activo) return;

        if (refs.tipo.value === "si_no") {
            refs.puntajeSiNoWrap.classList.remove("d-none");
        } else if (tiposConOpciones.indexOf(refs.tipo.value) !== -1) {
            refs.puntajeOpcionesWrap.classList.remove("d-none");
            actualizarFilasPuntajeOpciones(refs);
        } else if (refs.tipo.value === "escala") {
            refs.puntajeEscalaNota.classList.remove("d-none");
        }
    }

    /** Muestra u oculta el switch "¿Pondera?" según si el tipo de pregunta
     * tiene un conjunto fijo de valores posibles. */
    function actualizarVisibilidadPondera(refs) {
        var esPonderable = tiposPonderables.indexOf(refs.tipo.value) !== -1;
        refs.ponderaWrap.classList.toggle("d-none", !esPonderable);
        if (!esPonderable) {
            refs.pondera.checked = false;
        }
        actualizarDetallePondera(refs);
    }

    function crearFila(datosIniciales) {
        var fragmento = template.content.cloneNode(true);
        var fila = fragmento.querySelector(".pregunta-row");

        var refs = {
            numero: fila.querySelector(".pregunta-numero"),
            quitarBtn: fila.querySelector(".btn-quitar-pregunta"),
            arrastrar: fila.querySelector(".pregunta-arrastrar"),
            texto: fila.querySelector(".pregunta-texto"),
            bloque: fila.querySelector(".pregunta-bloque"),
            maxCaracteres: fila.querySelector(".pregunta-max-caracteres"),
            maxCaracteresWrap: fila.querySelector(".pregunta-max-caracteres-wrap"),
            tipo: fila.querySelector(".pregunta-tipo"),
            obligatoria: fila.querySelector(".pregunta-obligatoria"),
            opcionesWrap: fila.querySelector(".pregunta-opciones-wrap"),
            opciones: fila.querySelector(".pregunta-opciones"),
            condicionWrap: fila.querySelector(".pregunta-condicion-wrap"),
            condicionRef: fila.querySelector(".pregunta-condicion-referencia"),
            condicionOperador: fila.querySelector(".pregunta-condicion-operador"),
            condicionValor: fila.querySelector(".pregunta-condicion-valor"),
            condicionValorSelect: fila.querySelector(".pregunta-condicion-valor-select"),
            ponderaWrap: fila.querySelector(".pregunta-pondera-wrap"),
            pondera: fila.querySelector(".pregunta-pondera"),
            ponderaDetalle: fila.querySelector(".pregunta-puntaje-detalle"),
            puntajeSiNoWrap: fila.querySelector(".pregunta-puntaje-si-no"),
            puntajeSi: fila.querySelector(".pregunta-puntaje-si"),
            puntajeNo: fila.querySelector(".pregunta-puntaje-no"),
            puntajeOpcionesWrap: fila.querySelector(".pregunta-puntaje-opciones-wrap"),
            puntajeOpcionesList: fila.querySelector(".pregunta-puntaje-opciones-list"),
            puntajeEscalaNota: fila.querySelector(".pregunta-puntaje-escala-nota"),
            _puntajesPorOpcion: {},
        };

        refs.tipo.addEventListener("change", function () {
            actualizarVisibilidadOpciones(refs);
            actualizarVisibilidadPondera(refs);
            refrescarCondicionesValor();
        });
        refs.opciones.addEventListener("input", function () {
            actualizarDetallePondera(refs);
            refrescarCondicionesValor();
        });
        refs.pondera.addEventListener("change", function () {
            actualizarDetallePondera(refs);
        });
        refs.condicionRef.addEventListener("change", function () {
            refs._condicionFila = container.children[parseInt(refs.condicionRef.value, 10) - 1] || null;
            actualizarValorCondicion(refs);
        });
        refs.arrastrar.addEventListener("keydown", function (event) {
            if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
            event.preventDefault();
            var desplazamiento = event.key === "ArrowUp" ? -1 : 1;
            moverFila(fila, Array.from(container.children).indexOf(fila) + desplazamiento);
            refs.arrastrar.focus({ preventScroll: true });
        });
        refs.arrastrar.addEventListener("dragstart", function (event) {
            filaArrastrada = fila;
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", refs.numero.textContent);
            var rect = fila.getBoundingClientRect();
            event.dataTransfer.setDragImage(fila, event.clientX - rect.left, event.clientY - rect.top);
            // El navegador captura primero la tarjeta completa; después atenuamos su lugar de origen.
            requestAnimationFrame(function () {
                if (filaArrastrada === fila) fila.classList.add("pregunta-arrastrando");
            });
        });
        refs.arrastrar.addEventListener("dragend", function () {
            detenerScrollArrastre();
            filaArrastrada = null;
            fila.classList.remove("pregunta-arrastrando");
            limpiarDestinoArrastre();
        });
        fila.addEventListener("dragover", function (event) {
            if (!filaArrastrada) return;
            event.preventDefault();
            event.dataTransfer.dropEffect = "move";
            // El espacio modifica la geometría bajo el cursor. Mantenerlo hasta
            // entrar en otra tarjeta evita ciclos de dragleave/dragover y saltos.
            if (fila === destinoArrastre || fila === filaArrastrada) return;
            limpiarDestinoArrastre();
            destinoArrastre = fila;
            var filas = Array.from(container.children);
            fila.classList.add(filas.indexOf(filaArrastrada) < filas.indexOf(fila)
                ? "pregunta-destino-despues" : "pregunta-destino-antes");
        });
        fila.addEventListener("drop", function (event) {
            if (!filaArrastrada) return;
            event.preventDefault();
            detenerScrollArrastre();
            soltarFila(fila);
        });
        refs.texto.addEventListener("input", renumerarFilas);
        refs.quitarBtn.addEventListener("click", function () {
            var advertencia = "¿Quitar la " + refs.numero.textContent.toLowerCase()
                + "? Se eliminarán su texto, opciones y configuración. El cambio se aplicará al guardar la encuesta.";
            var tieneDependientes = Array.from(container.children).some(function (otra) {
                return otra._preguntaRefs._condicionFila === fila;
            });
            if (tieneDependientes) {
                advertencia += " Las preguntas que dependen de esta quedarán siempre visibles.";
            }
            filaPorQuitar = fila;
            advertenciaQuitarEl.textContent = advertencia;
            modalQuitar.show();
        });

        fila._preguntaRefs = refs;
        container.appendChild(fila);

        if (datosIniciales) {
            refs.texto.value = datosIniciales.texto || "";
            refs.bloque.value = datosIniciales.bloque || "";
            refs.maxCaracteres.value = datosIniciales.max_caracteres || "";
            refs.tipo.value = datosIniciales.tipo || refs.tipo.value;
            refs.obligatoria.checked = datosIniciales.obligatoria !== false;
            var opcionesIniciales = (datosIniciales.opciones || []).map(function (opcion) {
                return typeof opcion === "object" ? opcion : { texto: opcion, puntaje: 0 };
            });
            refs.opciones.value = opcionesIniciales
                .map(function (opcion) { return opcion.texto; })
                .join("\n");
            opcionesIniciales.forEach(function (opcion) {
                refs._puntajesPorOpcion[opcion.texto] = opcion.puntaje || 0;
            });
            refs.pondera.checked = Boolean(datosIniciales.pondera);
            refs.puntajeSi.value = datosIniciales.puntaje_si || 0;
            refs.puntajeNo.value = datosIniciales.puntaje_no || 0;
        }
        actualizarVisibilidadOpciones(refs);
        actualizarVisibilidadPondera(refs);

        renumerarFilas();
        actualizarVacioMsg();
        return refs;
    }

    /** Aplica la condición guardada una vez que todas las filas ya existen
     * (necesita que el select de referencia ya tenga las opciones cargadas). */
    function aplicarCondicionesIniciales(datosPorFila) {
        var filas = Array.from(container.children);
        filas.forEach(function (fila, indice) {
            var datos = datosPorFila[indice];
            if (!datos || !datos.condicion) return;
            var refs = fila._preguntaRefs;
            refs.condicionRef.value = String(datos.condicion.orden);
            refs._condicionFila = filas[datos.condicion.orden - 1];
            refs.condicionOperador.value = datos.condicion.operador;
            actualizarValorCondicion(refs);
            escribirValorCondicionActivo(refs, datos.condicion.valor);
        });
    }

    addBtn.addEventListener("click", function () { crearFila(); });

    function serializarPreguntas() {
        var filas = Array.from(container.children);
        return filas.map(function (fila, indice) {
            var refs = fila._preguntaRefs;
            var orden = indice + 1;
            var item = {
                orden: orden,
                texto: refs.texto.value.trim(),
                bloque: refs.bloque.value.trim(),
                max_caracteres: refs.maxCaracteres.value ? Number(refs.maxCaracteres.value) : null,
                tipo: refs.tipo.value,
                obligatoria: refs.obligatoria.checked,
                opciones: refs.opciones.value
                    .split("\n")
                    .map(function (linea) { return linea.trim(); })
                    .filter(Boolean)
                    .map(function (texto) {
                        return {
                            texto: texto,
                            puntaje: parseInt(refs._puntajesPorOpcion[texto], 10) || 0,
                        };
                    }),
                pondera: refs.pondera.checked,
                puntaje_si: parseInt(refs.puntajeSi.value, 10) || 0,
                puntaje_no: parseInt(refs.puntajeNo.value, 10) || 0,
                condicion: null,
            };
            if (refs.condicionRef.value) {
                item.condicion = {
                    orden: parseInt(refs.condicionRef.value, 10),
                    operador: refs.condicionOperador.value,
                    valor: leerValorCondicionActivo(refs).trim(),
                };
            }
            return item;
        });
    }

    form.addEventListener("submit", function () {
        hiddenInput.value = JSON.stringify(serializarPreguntas());
    });

    // Hidratación inicial: datos existentes (editar) o el último intento
    // fallido (si el formulario volvió con errores).
    var datosIniciales = [];
    if (initialDataEl) {
        try {
            datosIniciales = JSON.parse(initialDataEl.textContent) || [];
        } catch (e) {
            datosIniciales = [];
        }
    }
    datosIniciales.forEach(function (datos) { crearFila(datos); });
    aplicarCondicionesIniciales(datosIniciales);
    actualizarVacioMsg();
})();
