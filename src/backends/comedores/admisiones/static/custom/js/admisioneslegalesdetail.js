
// --- Modal Documento Expediente ---
document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("modalDocumentoExpediente");
    if (modal) {
        modal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const tipo = button.getAttribute("data-bs-tipo");
            const label = button.getAttribute("data-bs-label");

            const tipoInput = modal.querySelector("#tipo_id");
            if (tipoInput) tipoInput.value = tipo;

            const modalTitle = modal.querySelector("#modalDocumentoExpedienteLabel");
            if (modalTitle) modalTitle.textContent = tipo;

            const modalLabel = modal.querySelector("#valueLabel");
            if (modalLabel) modalLabel.textContent = label;
        });
    }

    // --- Intervención Jurídicos ---
    const selectIntervencion = document.getElementById("id_intervencion_juridicos");
    const motivoField = document.getElementById("motivoRechazoField");
    const dictamenField = document.getElementById("motivoDictamenField");
    const motivoSelect = document.getElementById("id_rechazo_juridicos_motivo");
    const dictamenInput = document.getElementById("id_dictamen_motivo");

    function toggleMotivos() {
        if (selectIntervencion && selectIntervencion.value === "rechazado") {
            if (motivoField) motivoField.style.display = "block";
            if (motivoSelect) motivoSelect.required = true;

            if (motivoSelect && motivoSelect.value === "dictamen") {
                if (dictamenField) dictamenField.style.display = "block";
                if (dictamenInput) dictamenInput.required = true;
            } else {
                if (dictamenField) dictamenField.style.display = "none";
                if (dictamenInput) {
                    dictamenInput.required = false;
                    dictamenInput.value = "";
                }
            }
        } else {
            if (motivoField) motivoField.style.display = "none";
            if (dictamenField) dictamenField.style.display = "none";

            if (motivoSelect) {
                motivoSelect.required = false;
                motivoSelect.value = "";
            }
            if (dictamenInput) {
                dictamenInput.required = false;
                dictamenInput.value = "";
            }
        }
    }

    if (selectIntervencion) {
        selectIntervencion.addEventListener("change", toggleMotivos);
    }
    if (motivoSelect) {
        motivoSelect.addEventListener("change", toggleMotivos);
    }

    toggleMotivos();
});

document.addEventListener("DOMContentLoaded", () => {
    const provincia = document.getElementById("id_proyecto_autoridad_provincia");
    const localidad = document.getElementById("id_proyecto_autoridad_localidad");
    if (!provincia || !localidad) return;

    const grupo = provincia.closest("[data-localidades-url]");
    const error = grupo.querySelector("[data-localidades-error]");
    let carga;
    provincia.addEventListener("change", async () => {
        carga?.abort();
        localidad.replaceChildren(new Option("---------", ""));
        error.hidden = true;
        if (!provincia.value) return;

        carga = new AbortController();
        const url = new URL(grupo.dataset.localidadesUrl, window.location.origin);
        url.searchParams.set("provincia_id", provincia.value);
        try {
            const respuesta = await fetch(url, { signal: carga.signal });
            if (!respuesta.ok) throw new Error("No se pudieron cargar las localidades");
            const opciones = await respuesta.json();
            localidad.append(...opciones.map(({ id, nombre }) => new Option(nombre, id)));
        } catch (fallo) {
            if (fallo.name !== "AbortError") error.hidden = false;
        }
    });
});
