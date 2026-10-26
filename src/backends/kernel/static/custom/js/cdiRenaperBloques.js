/**
 * CDI - VALIDACIÓN RENAPER POR BLOQUE
 *
 * Cada persona del formulario (niño/a, responsables, referente) es un "bloque"
 * con cuatro estados:
 *   agregar    -> bloque opcional sin usar: solo el botón "Agregar ..."
 *   dni        -> solo tipo de documento + DNI + "Validar con RENAPER"
 *   verificado -> tarjeta de solo lectura con la identidad + campos a completar
 *   manual     -> todos los campos editables
 *
 * El servidor es quien bloquea: toma la identidad del token firmado, no de los
 * inputs. Este script solo ordena la pantalla. Sin JS se ven todos los campos.
 */

document.addEventListener("DOMContentLoaded", function () {
    const bloques = document.querySelectorAll("[data-renaper-bloque]");
    bloques.forEach(initializeRenaperBloque);
    // Un campo obligatorio oculto bloquea el envío sin avisar: si el navegador
    // marca uno, se avisa en el bloque para que se valide el DNI.
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("invalid", abrirBloqueDelCampoInvalido, true);
    });
});

// ─────────────────────────────────────────────────────────
// ESTRUCTURA DEL BLOQUE
// ─────────────────────────────────────────────────────────

function camposIdentidad(container) {
    return (container.dataset.renaperCampos || "").split(",").filter(Boolean);
}

function inputDeCampo(nombreCampo) {
    return document.getElementById("id_" + nombreCampo);
}

function inputDni(container) {
    return document.getElementById(container.dataset.dniInput);
}

function inputTipo(container) {
    return container.dataset.tipoInput
        ? document.getElementById(container.dataset.tipoInput)
        : null;
}

function alcanceDelBloque(container) {
    return container.closest(".section-body") || container.parentElement;
}

function columnasDelBloque(container) {
    return Array.from(alcanceDelBloque(container).querySelectorAll(".row > [class*='col-']"))
        .filter(function (col) { return col.querySelector("input, select, textarea"); });
}

function columnaDe(input) {
    return input ? input.closest("[class*='col-']") : null;
}

function estaBloqueado(input) {
    return Boolean(input && input.dataset.renaper === "1");
}

// ─────────────────────────────────────────────────────────
// ESTADOS
// ─────────────────────────────────────────────────────────

function setModo(container, modo) {
    container.dataset.renaperModo = modo;
    container.querySelectorAll("[data-renaper-panel]").forEach(function (panel) {
        panel.hidden = panel.dataset.renaperPanel !== modo;
    });

    const dniCol = columnaDe(inputDni(container));
    const tipoCol = columnaDe(inputTipo(container));
    columnasDelBloque(container).forEach(function (col) {
        let visible = true;
        if (modo === "agregar") {
            visible = false;
        } else if (modo === "dni") {
            visible = col === dniCol || col === tipoCol;
        } else if (modo === "verificado") {
            // Lo que vino de RENAPER se ve en la tarjeta; lo demás se completa.
            visible = !estaBloqueado(col.querySelector("input, select, textarea"));
        }
        col.hidden = !visible;
    });

    if (modo === "verificado") renderizarTarjeta(container);
}

function enfocarDni(container) {
    const dni = inputDni(container);
    if (dni && !dni.disabled) dni.focus();
}

function initializeRenaperBloque(container) {
    let modo = container.dataset.renaperModo || "manual";
    if (modo === "dni" && container.dataset.opcional === "1") modo = "agregar";
    setModo(container, modo);

    container.querySelectorAll("[data-renaper-consultar]").forEach(function (boton) {
        boton.addEventListener("click", function () { consultarRenaper(container, boton); });
    });
    const agregar = container.querySelector("[data-renaper-agregar]");
    if (agregar) {
        agregar.addEventListener("click", function () {
            setModo(container, "dni");
            enfocarDni(container);
        });
    }
    const manual = container.querySelector("[data-renaper-manual]");
    if (manual) manual.addEventListener("click", function () { pasarAManual(container); });
    const cambiar = container.querySelector("[data-renaper-cambiar]");
    if (cambiar) cambiar.addEventListener("click", function () { cambiarPersona(container); });
    const cancelar = container.querySelector("[data-renaper-cancelar]");
    if (cancelar) cancelar.addEventListener("click", function () { cancelarCambio(container); });

    const dni = inputDni(container);
    if (dni) {
        dni.addEventListener("keydown", function (event) {
            // Enter en el DNI valida en vez de enviar todo el formulario.
            if (event.key !== "Enter" || container.dataset.renaperModo !== "dni") return;
            event.preventDefault();
            consultarRenaper(container, container.querySelector("[data-renaper-panel='dni'] [data-renaper-consultar]"));
        });
    }

    const tipo = inputTipo(container);
    if (tipo) {
        tipo.addEventListener("change", function () {
            const conDni = (container.dataset.tiposConDni || "").split(",");
            if (container.dataset.renaperModo === "dni" && tipo.value && !conDni.includes(tipo.value)) {
                pasarAManual(container);
                mostrarMensaje(container, "Sin DNI no hay datos para consultar en RENAPER: completá los datos manualmente.", false);
            }
        });
    }
}

function abrirBloqueDelCampoInvalido(event) {
    const col = columnaDe(event.target);
    if (!col || !col.hidden) return;
    const seccion = event.target.closest(".section-body");
    const container = seccion && seccion.querySelector("[data-renaper-bloque]");
    if (!container) return;
    // No se abre la carga manual: la persona tiene que pasar por RENAPER primero.
    if (container.dataset.renaperModo === "agregar") setModo(container, "dni");
    mostrarMensaje(container, "Falta completar esta persona: validá el DNI con RENAPER.", true);
    container.scrollIntoView({ block: "center" });
    enfocarDni(container);
}

// ─────────────────────────────────────────────────────────
// TARJETA
// ─────────────────────────────────────────────────────────

function etiquetaDe(input) {
    const label = document.querySelector("label[for='" + input.id + "']");
    return label ? label.textContent.replace("*", "").trim() : input.name;
}

function valorVisible(input) {
    if (input.tagName === "SELECT") {
        const opcion = input.options[input.selectedIndex];
        return opcion && opcion.value ? opcion.text : "";
    }
    if (/(cuit|cuil)/.test(input.name)) {
        const digitos = input.value.replace(/\D/g, "");
        if (digitos.length === 11) {
            return digitos.slice(0, 2) + "-" + digitos.slice(2, 10) + "-" + digitos.slice(10);
        }
    }
    if (input.type === "date" && /^\d{4}-\d{2}-\d{2}$/.test(input.value)) {
        const [anio, mes, dia] = input.value.split("-");
        return dia + "/" + mes + "/" + anio;
    }
    return input.value;
}

function renderizarTarjeta(container) {
    const datos = container.querySelector("[data-renaper-datos]");
    if (!datos) return;
    datos.replaceChildren();
    camposIdentidad(container).forEach(function (nombreCampo) {
        const input = inputDeCampo(nombreCampo);
        if (!estaBloqueado(input)) return;
        const item = document.createElement("div");
        item.className = "col-md-3 mb-2";
        const dt = document.createElement("dt");
        dt.className = "small fw-normal";
        dt.style.color = "#9ca3af";
        dt.textContent = etiquetaDe(input);
        const dd = document.createElement("dd");
        dd.className = "mb-0";
        dd.style.color = "#e5e7eb";
        dd.textContent = valorVisible(input) || "—";
        item.append(dt, dd);
        datos.append(item);
    });
}

// ─────────────────────────────────────────────────────────
// ACCIONES
// ─────────────────────────────────────────────────────────

function mostrarMensaje(container, texto, esError) {
    const mensaje = container.querySelector("[data-renaper-mensaje]");
    if (!mensaje) return;
    mensaje.textContent = texto;
    mensaje.style.color = esError ? "#f87171" : "#9ca3af";
}

function bloquearCampo(input) {
    input.dataset.renaper = "1";
    if (input.tagName === "SELECT") {
        // Un select no admite readonly: se evita la interacción pero se sigue enviando.
        input.style.pointerEvents = "none";
        input.setAttribute("tabindex", "-1");
        input.setAttribute("aria-readonly", "true");
    } else {
        input.readOnly = true;
    }
}

function liberarCampo(input, limpiar) {
    delete input.dataset.renaper;
    input.disabled = false;
    input.readOnly = false;
    input.style.pointerEvents = "";
    input.removeAttribute("tabindex");
    input.removeAttribute("aria-readonly");
    if (limpiar) {
        input.value = "";
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }
}

const INSTRUCCION_DNI = "Ingresá el DNI y validalo con RENAPER: los datos de identidad se completan solos.";

function setInstruccion(container, texto) {
    const instruccion = container.querySelector("[data-renaper-instruccion]");
    if (instruccion) instruccion.textContent = texto || INSTRUCCION_DNI;
}

function mostrarBotonManual(container, visible) {
    const manual = container.querySelector("[data-renaper-manual]");
    if (manual) manual.hidden = !visible;
}

function ofrecerCargaManual(container) {
    // La carga manual es la alternativa cuando RENAPER no encuentra a la persona
    // o no responde. Una persona ya guardada como verificada solo se reemplaza
    // validando a otra: el servidor ignoraría la carga manual.
    if (container.dataset.verificadoServidor === "1") return;
    mostrarBotonManual(container, true);
}

function tokenInput(container) {
    return container.querySelector("input[name^='renaper_token_']");
}

function pasarAManual(container) {
    // Una precarga de esta pantalla que todavía no se guardó se descarta entera.
    if (tokenInput(container).value) {
        tokenInput(container).value = "";
        camposIdentidad(container).forEach(function (nombreCampo) {
            const input = inputDeCampo(nombreCampo);
            if (input && estaBloqueado(input)) liberarCampo(input, true);
        });
    }
    mostrarMensaje(container, "", false);
    setModo(container, "manual");
}

function cambiarPersona(container) {
    // Solo se libera el DNI: el resto sigue con los datos actuales hasta que
    // RENAPER confirme a la persona nueva, y "Cancelar" vuelve atrás.
    const dni = inputDni(container);
    container.dataset.dniAnterior = dni.value;
    liberarCampo(dni, true);
    container.querySelector("[data-renaper-cancelar]").hidden = false;
    mostrarBotonManual(container, false);
    setInstruccion(container, "Ingresá el DNI de la nueva persona y validalo con RENAPER.");
    mostrarMensaje(container, "", false);
    setModo(container, "dni");
    enfocarDni(container);
}

function cancelarCambio(container) {
    const dni = inputDni(container);
    dni.value = container.dataset.dniAnterior || "";
    bloquearCampo(dni);
    container.querySelector("[data-renaper-cancelar]").hidden = true;
    setInstruccion(container, null);
    mostrarMensaje(container, "", false);
    setModo(container, "verificado");
}

function aplicarValores(container, valores) {
    camposIdentidad(container).forEach(function (nombreCampo) {
        const input = inputDeCampo(nombreCampo);
        if (!input) return;
        if (Object.prototype.hasOwnProperty.call(valores, nombreCampo)) {
            liberarCampo(input, false);
            input.value = valores[nombreCampo];
            input.dispatchEvent(new Event("change", { bubbles: true }));
            bloquearCampo(input);
        } else if (estaBloqueado(input)) {
            // Dato de la persona anterior que la nueva no trae: queda para completar.
            liberarCampo(input, true);
        }
    });
}

async function consultarRenaper(container, boton) {
    const dniInput = inputDni(container);
    const dni = ((dniInput && dniInput.value) || "").replace(/\D/g, "");
    if (dni.length < 7) {
        mostrarMensaje(container, "Ingresá un DNI de 7 u 8 dígitos.", true);
        if (dniInput) dniInput.focus();
        return;
    }

    if (boton) boton.disabled = true;
    mostrarMensaje(container, "Consultando RENAPER...", false);
    try {
        const url = container.dataset.renaperUrl + "?dni=" + encodeURIComponent(dni);
        const response = await fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin",
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            mostrarMensaje(container, (data && data.message) || "No se encontraron datos en RENAPER.", true);
            ofrecerCargaManual(container);
            return;
        }
        aplicarValores(container, data.valores);
        tokenInput(container).value = data.token;
        container.querySelector("[data-renaper-cancelar]").hidden = true;
        mostrarBotonManual(container, false);
        setInstruccion(container, null);
        mostrarMensaje(container, "", false);
        setModo(container, "verificado");
    } catch (error) {
        mostrarMensaje(container, "No se pudo consultar RENAPER. Intentá de nuevo.", true);
        ofrecerCargaManual(container);
    } finally {
        if (boton) boton.disabled = false;
    }
}
