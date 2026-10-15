/* Panel de Inspecciones escolares (backoffice).
 *
 * Todo se engancha por atributos data-insp-*, sin handlers inline (CSP):
 * - data-insp-select2="<url>": Select2 con búsqueda AJAX. data-insp-min (letras
 *   mínimas), data-insp-provincia="#select" (filtra por esa provincia).
 * - data-insp-limpia="#select": al cambiar, vacía ese select dependiente.
 * - data-insp-auto-submit: envía el formulario de filtros al cambiar.
 * - data-insp-modal-url="<url>": abre el modal con el formulario de esa URL.
 * - data-insp-abrir-modal="<url>": lo abre al cargar la página.
 * - data-insp-confirmar="<texto>": pide confirmación antes de enviar.
 * - data-insp-procesando="<texto>": deshabilita el envío y avisa que procesa.
 */
(function ($) {
    "use strict";

    const modalEl = document.getElementById("insp-modal-form");

    function escapar(texto) {
        const div = document.createElement("div");
        div.textContent = texto == null ? "" : String(texto);
        return div.innerHTML;
    }

    function plantilla(opcion) {
        if (!opcion.id || !opcion.detalle) {
            return escapar(opcion.text);
        }
        return $(
            "<span>" + escapar(opcion.text) +
            '<span class="insp-opcion-detalle">' + escapar(opcion.detalle) + "</span></span>"
        );
    }

    function iniciarSelect2(contexto) {
        $(contexto).find("[data-insp-select2]").each(function () {
            const $select = $(this);
            if ($select.data("select2")) {
                return;
            }
            const minimo = parseInt($select.data("insp-min") || 0, 10);
            const provincia = $select.data("insp-provincia");
            // El desplegable se cuelga del modal o de la sección con tema claro, no del body oscuro.
            const $modal = $select.closest(".modal, [data-bs-theme]");
            $select.select2({
                width: $select.closest(".insp-filtros").length ? "style" : "100%",
                allowClear: true,
                placeholder: $select.data("placeholder") || "",
                minimumInputLength: minimo,
                dropdownParent: $modal.length ? $modal : $(document.body),
                language: {
                    inputTooShort: function () {
                        return "Escribí al menos " + minimo + " letras";
                    },
                    noResults: function () {
                        return "Sin resultados";
                    },
                    searching: function () {
                        return "Buscando…";
                    },
                },
                templateResult: plantilla,
                ajax: {
                    url: $select.data("insp-select2"),
                    dataType: "json",
                    delay: 250,
                    data: function (params) {
                        const datos = { q: params.term || "" };
                        if (provincia) {
                            datos.provincia = $(provincia).val() || "";
                        }
                        return datos;
                    },
                },
            });
        });
    }

    function iniciarDependientes(contexto) {
        $(contexto).find("[data-insp-limpia]").each(function () {
            const $origen = $(this);
            $origen.on("change", function () {
                const $destino = $($origen.data("insp-limpia"));
                $destino.val(null).trigger("change.select2");
                $destino.prop("disabled", !$origen.val());
            });
        });
    }

    function enviar(form) {
        if (form.requestSubmit) {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    function iniciarFormulariosDeFiltro() {
        $(document).on("change", "form [data-insp-auto-submit]", function () {
            // La provincia vacía también limpia la localidad antes de enviar.
            enviar(this.form);
        });
    }

    function iniciarConfirmaciones() {
        $(document).on("submit", "form[data-insp-confirmar]", function (evento) {
            if (!window.confirm(this.dataset.inspConfirmar)) {
                evento.preventDefault();
            }
        });
        $(document).on("submit", "form[data-insp-procesando]", function () {
            $(this).find("[type=submit]").prop("disabled", true);
            const aviso = document.createElement("div");
            aviso.className = "small text-muted mt-2 px-3 pb-2";
            aviso.setAttribute("role", "status");
            aviso.textContent = this.dataset.inspProcesando;
            this.appendChild(aviso);
        });
    }

    /* --- Formularios en el modal ------------------------------------- */

    function contenidoModal() {
        return modalEl.querySelector("[data-insp-modal-contenido]");
    }

    function pintarFormulario(html, mensaje) {
        const contenedor = contenidoModal();
        contenedor.innerHTML = html;
        iniciarSelect2(contenedor);
        iniciarDependientes(contenedor);
        iniciarVerificacion(contenedor);
        if (mensaje) {
            const lugar = contenedor.querySelector("[data-insp-mensaje]");
            if (lugar) {
                lugar.innerHTML =
                    '<div class="alert alert-success" role="status">' + escapar(mensaje) + "</div>";
            }
        }
        const primero = contenedor.querySelector("input:not([type=hidden]), select");
        if (primero) {
            primero.focus();
        }
    }

    function cargarFormulario(url, mensaje) {
        return fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
        })
            .then(function (respuesta) {
                return respuesta.text();
            })
            .then(function (html) {
                pintarFormulario(html, mensaje);
            });
    }

    function abrirModal(url) {
        contenidoModal().innerHTML =
            '<div class="modal-body text-center text-muted py-5">Cargando…</div>';
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
        cargarFormulario(url);
    }

    function otraConFecha(form) {
        const fecha = form.querySelector("[name=fecha]");
        return fecha && fecha.value ? "?fecha=" + encodeURIComponent(fecha.value) : "";
    }

    function enviarFormulario(evento) {
        const form = evento.target.closest("form[data-insp-form-modal]");
        if (!form) {
            return;
        }
        evento.preventDefault();
        const datos = new FormData(form);
        if (evento.submitter && evento.submitter.name) {
            datos.append(evento.submitter.name, evento.submitter.value);
        }
        $(form).find("[type=submit]").prop("disabled", true);
        fetch(form.action, {
            method: "POST",
            body: datos,
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
        }).then(function (respuesta) {
            const tipo = respuesta.headers.get("content-type") || "";
            if (tipo.indexOf("application/json") !== -1) {
                return respuesta.json().then(function (json) {
                    if (json.otra) {
                        cargarFormulario(form.action.split("?")[0] + otraConFecha(form), json.mensaje);
                    } else {
                        window.location.reload();
                    }
                });
            }
            return respuesta.text().then(function (html) {
                pintarFormulario(html);
            });
        });
    }

    /* --- Aviso de escuela ya asignada en la jornada ------------------- */

    function iniciarVerificacion(contexto) {
        const form = contexto.querySelector("form[data-insp-verificar]");
        if (!form) {
            return;
        }
        const aviso = form.querySelector("[data-insp-aviso-duplicada]");
        function verificar() {
            const datos = new URLSearchParams();
            ["fecha", "inspector", "escuela"].forEach(function (campo) {
                const control = form.querySelector("[name=" + campo + "]");
                datos.append(campo, control ? control.value || "" : "");
            });
            if (!datos.get("escuela") || !datos.get("fecha")) {
                aviso.classList.add("d-none");
                return;
            }
            fetch(form.dataset.inspVerificar + "?" + datos.toString(), {
                credentials: "same-origin",
            })
                .then(function (respuesta) {
                    return respuesta.json();
                })
                .then(function (json) {
                    if (json.otras && json.otras.length) {
                        aviso.textContent =
                            json.escuela + " ya está asignada en esta jornada a " +
                            json.otras.join(", ") +
                            ". Podés asignarla igual: cuenta como otra visita y no reemplaza la anterior.";
                        aviso.classList.remove("d-none");
                    } else {
                        aviso.classList.add("d-none");
                    }
                });
        }
        $(form).find("[data-insp-verifica]").on("change", verificar);
        verificar();
    }

    $(function () {
        iniciarSelect2(document);
        iniciarDependientes(document);
        iniciarFormulariosDeFiltro();
        iniciarConfirmaciones();
        if (!modalEl) {
            return;
        }
        $(document).on("click", "[data-insp-modal-url]", function () {
            abrirModal(this.dataset.inspModalUrl);
        });
        modalEl.addEventListener("submit", enviarFormulario);
        const automatico = document.querySelector("[data-insp-abrir-modal]");
        if (automatico) {
            abrirModal(automatico.dataset.inspAbrirModal);
        }
    });
})(window.jQuery);
