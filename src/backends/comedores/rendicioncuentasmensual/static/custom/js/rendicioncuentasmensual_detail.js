document.addEventListener("DOMContentLoaded", function () {
    const feedback = document.getElementById("revision-feedback");
    const selectoresEstado = document.querySelectorAll(".js-documento-estado");
    const statusBadge = document.getElementById("rendicion-estado-badge");
    const downloadAction = document.getElementById("rendicion-download-action");
    const downloadUrl = "./descargar-pdf/";

    const escapeHtml = function (value) {
        const container = document.createElement("div");
        container.textContent = value || "";
        return container.innerHTML;
    };

    const renderRendicionBadge = function (estado, label) {
        if (!statusBadge) {
            return;
        }

        statusBadge.textContent = label;
        statusBadge.className = "badge-validacion";
        if (estado === "finalizada") {
            statusBadge.classList.add("validado");
            return;
        }
        if (estado === "subsanar") {
            statusBadge.classList.add("no-validado");
            return;
        }
        statusBadge.classList.add("pendiente");
    };

    const renderDownloadAction = function (enabled, customUrl) {
        if (!downloadAction) {
            return;
        }
        if (!enabled) {
            downloadAction.innerHTML = "";
            return;
        }

        const href = customUrl || downloadUrl;
        downloadAction.innerHTML =
            '<a href="' +
            href +
            '" class="btn btn-sm btn-success">' +
            '<i class="fas fa-file-pdf"></i> Generar descarga</a>';
    };

    const showFeedback = function (message, kind) {
        if (!feedback) {
            return;
        }
        feedback.textContent = message;
        feedback.className = "alert mb-3";
        feedback.classList.add(kind === "error" ? "alert-danger" : "alert-success");
    };

    const renderEstadoBadge = function (estadoVisual, estadoLabelVisual) {
        let badgeClass = "badge-validacion pendiente";
        if (estadoVisual === "validado") {
            badgeClass = "badge-validacion validado";
        } else if (estadoVisual === "subsanar") {
            badgeClass = "badge-validacion no-validado";
        }

        return (
            '<span class="' + badgeClass + '">' + estadoLabelVisual + "</span>"
        );
    };

    const setSubmitterLoading = function (submitter, isLoading) {
        if (!submitter) {
            return;
        }

        submitter.disabled = isLoading;
        const idle = submitter.querySelector(".js-submit-idle");
        const spinner = submitter.querySelector(".js-submit-spinner");

        if (idle) {
            idle.classList.toggle("d-none", isLoading);
        }
        if (spinner) {
            spinner.classList.toggle("d-none", !isLoading);
        }
    };

    selectoresEstado.forEach(function (selector) {
        const documentoId = selector.dataset.documentoId;
        const form = document.getElementById("revision-documento-" + documentoId);
        const observacionesInput = document.getElementById(
            "observaciones-" + documentoId
        );
        const observacionesRow = document.getElementById(
            "observaciones-row-" + documentoId
        );
        const botonGuardar = document.getElementById(
            "guardar-revision-inline-" + documentoId
        );
        const botonGuardarObservaciones = document.getElementById(
            "guardar-revision-observaciones-" + documentoId
        );

        const actualizarFilaRevision = function () {
            const estadoSeleccionado = selector.value;
            const mostrarObservaciones = estadoSeleccionado === "subsanar";
            const mostrarGuardarInline = estadoSeleccionado === "validado";
            const mostrarGuardarObservaciones = estadoSeleccionado === "subsanar";

            if (observacionesInput) {
                observacionesInput.required = mostrarObservaciones;
                if (!mostrarObservaciones) {
                    observacionesInput.value = "";
                }
            }

            if (observacionesRow) {
                const observacionPrevia = document.getElementById(
                    "observaciones-display-" + documentoId
                );
                observacionesRow.classList.toggle(
                    "d-none", !mostrarObservaciones && !observacionPrevia
                );
                if (observacionesInput) {
                    observacionesInput.parentElement.classList.toggle(
                        "d-none", !mostrarObservaciones
                    );
                }
            }

            if (botonGuardar) {
                botonGuardar.classList.toggle("d-none", !mostrarGuardarInline);
            }

            if (botonGuardarObservaciones) {
                botonGuardarObservaciones.classList.toggle(
                    "d-none",
                    !mostrarGuardarObservaciones
                );
            }
        };

        selector.addEventListener("change", actualizarFilaRevision);
        actualizarFilaRevision();

        if (!form) {
            return;
        }

        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const estadoSeleccionado = selector.value;
            const formData = new FormData(form);
            formData.set("estado", estadoSeleccionado);
            formData.set(
                "observaciones",
                observacionesInput ? observacionesInput.value.trim() : ""
            );

            const submitter =
                event.submitter && event.submitter.form === form
                    ? event.submitter
                    : null;

            setSubmitterLoading(submitter, true);

            fetch(window.location.href, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: formData,
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        if (!response.ok) {
                            throw new Error(
                                data.message || "No se pudo actualizar el documento."
                            );
                        }
                        return data;
                    });
                })
                .then(function (data) {
                    showFeedback(data.message, "success");

                    const estadoCell = document.getElementById(
                        "estado-cell-" + documentoId
                    );
                    if (estadoCell) {
                        estadoCell.innerHTML = renderEstadoBadge(
                            data.documento.estado_visual,
                            data.documento.estado_visual_display
                        );
                    }

                    window.location.reload();
                    renderRendicionBadge(
                        data.rendicion.estado,
                        data.rendicion.estado_display
                    );
                    renderDownloadAction(
                        data.rendicion.puede_descargar_pdf,
                        data.rendicion.download_url
                    );
                })
                .catch(function (error) {
                    showFeedback(error.message, "error");
                })
                .finally(function () {
                    setSubmitterLoading(submitter, false);
                });
        });
    });

    document
        .querySelectorAll(".js-solicitud-faltante-form")
        .forEach(function (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();

                const categoria = form.dataset.categoria;
                const submitter = event.submitter || form.querySelector("button[type='submit']");
                const input = form.querySelector("[name='observaciones_faltante']");
                const formData = new FormData(form);

                setSubmitterLoading(submitter, true);
                fetch(window.location.href, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData,
                })
                    .then(function (response) {
                        return response.json().then(function (data) {
                            if (!response.ok) {
                                throw new Error(
                                    data.message || "No se pudo registrar la solicitud."
                                );
                            }
                            return data;
                        });
                    })
                    .then(function (data) {
                        const badge = document.getElementById(
                            "solicitud-faltante-badge-" + categoria
                        );
                        const row = document.getElementById(
                            "solicitud-faltante-row-" + categoria
                        );
                        const observation = document.getElementById(
                            "solicitud-faltante-observacion-" + categoria
                        );

                        if (badge) badge.classList.remove("d-none");
                        if (row) row.classList.remove("d-none");
                        if (observation) {
                            observation.innerHTML =
                                "<strong>Observaciones:</strong> " +
                                escapeHtml(data.solicitud.observaciones);
                        }
                        if (input) input.value = "";
                        showFeedback(data.message, "success");
                    })
                    .catch(function (error) {
                        showFeedback(error.message, "error");
                    })
                    .finally(function () {
                        setSubmitterLoading(submitter, false);
                    });
            });
        });
});

// Actualizar la confirmación persistida al volver del visor de documentos.
(function () {
    let documentoAbierto = false;
    let salioDelDetalle = false;
    document.addEventListener("click", function (event) {
        if (
            event.target instanceof Element &&
            event.target.closest("a[data-refresh-visualizacion]")
        ) {
            documentoAbierto = true;
            salioDelDetalle = false;
        }
    });
    // Al guardar una revisión se quitan su selector y su textarea, así que
    // cualquier valor presente es una revisión todavía sin guardar.
    function hayRevisionesSinGuardar() {
        const observaciones = Array.from(
            document.querySelectorAll('textarea[name="observaciones"]')
        ).some(function (textarea) {
            return textarea.value.trim() !== "";
        });
        const estados = Array.from(
            document.querySelectorAll(".js-documento-estado")
        ).some(function (selector) {
            return selector.value !== "";
        });
        return observaciones || estados;
    }
    function registrarSalida() {
        if (documentoAbierto) {
            salioDelDetalle = true;
        }
    }
    function actualizarAlVolver() {
        if (document.visibilityState === "hidden") {
            registrarSalida();
            return;
        }
        // Sin salida real (pestaña en segundo plano) o con una revisión sin
        // guardar, se posterga la recarga para no perder lo que está en edición.
        if (!salioDelDetalle || hayRevisionesSinGuardar()) {
            return;
        }
        documentoAbierto = false;
        salioDelDetalle = false;
        window.location.reload();
    }
    window.addEventListener("blur", registrarSalida);
    window.addEventListener("focus", actualizarAlVolver);
    document.addEventListener("visibilitychange", actualizarAlVolver);
})();
