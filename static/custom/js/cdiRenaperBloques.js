/**
 * CDI - VALIDACIÓN RENAPER POR BLOQUE
 * Botón "Validar con RENAPER" junto al DNI de cada persona (niño/a, responsables,
 * referente). Precarga los datos, los deja de solo lectura y guarda el token
 * firmado que el servidor usa para bloquearlos: lo que se envíe en esos campos
 * se ignora.
 */

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-renaper-bloque]").forEach(initializeRenaperBloque);
});

function initializeRenaperBloque(container) {
    const boton = container.querySelector("[data-renaper-consultar]");
    if (!boton) return;
    boton.addEventListener("click", function () {
        consultarRenaper(container, boton);
    });
}

function mostrarMensajeRenaper(container, texto, esError) {
    const mensaje = container.querySelector("[data-renaper-mensaje]");
    if (!mensaje) return;
    mensaje.textContent = texto;
    mensaje.style.color = esError ? "#f87171" : "#34d399";
}

function bloquearCampoRenaper(campo) {
    campo.dataset.renaper = "1";
    if (campo.tagName === "SELECT") {
        // Un select no admite readonly: se evita la interacción pero se sigue enviando.
        campo.style.pointerEvents = "none";
        campo.setAttribute("tabindex", "-1");
        campo.setAttribute("aria-readonly", "true");
    } else {
        campo.readOnly = true;
    }
}

async function consultarRenaper(container, boton) {
    const dniInput = document.getElementById(container.dataset.dniInput);
    const dni = ((dniInput && dniInput.value) || "").replace(/\D/g, "");
    if (dni.length < 7) {
        mostrarMensajeRenaper(container, "Ingrese un DNI de 7 u 8 dígitos.", true);
        return;
    }

    boton.disabled = true;
    mostrarMensajeRenaper(container, "Consultando RENAPER...", false);
    try {
        const url = container.dataset.renaperUrl + "?dni=" + encodeURIComponent(dni);
        const response = await fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            mostrarMensajeRenaper(
                container,
                (data && data.message) || "No se encontraron datos en RENAPER. Puede cargarlos manualmente.",
                true
            );
            boton.disabled = false;
            return;
        }

        Object.entries(data.valores).forEach(function ([nombreCampo, valor]) {
            const campo = document.getElementById("id_" + nombreCampo);
            if (!campo) return;
            campo.value = valor;
            campo.dispatchEvent(new Event("change", { bubbles: true }));
            bloquearCampoRenaper(campo);
        });
        container.querySelector("input[type=hidden]").value = data.token;
        boton.remove();
        mostrarMensajeRenaper(container, "Datos verificados por RENAPER.", false);
    } catch (error) {
        mostrarMensajeRenaper(container, "No se pudo consultar RENAPER.", true);
        boton.disabled = false;
    }
}
