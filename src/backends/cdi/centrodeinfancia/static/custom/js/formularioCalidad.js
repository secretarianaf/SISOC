// Formulario de Calidad CDI: pases condicionales y campos "especificar".
// Las reglas vienen del schema vía data-attributes; el servidor vuelve a
// aplicarlas al guardar, así que esto sólo resuelve la experiencia en pantalla.
(function () {
    "use strict";

    const form = document.getElementById("formulario-calidad");
    if (!form) {
        return;
    }

    function valorDe(nombre) {
        const inputs = form.querySelectorAll(`[name="${nombre}"]`);
        for (const input of inputs) {
            if (input.type === "radio") {
                if (input.checked) {
                    return input.value;
                }
            } else if (input.type === "checkbox") {
                return input.checked ? "on" : "";
            } else {
                return input.value;
            }
        }
        return "";
    }

    function vaciar(contenedor) {
        contenedor.querySelectorAll("input, textarea, select").forEach((input) => {
            if (input.type === "radio" || input.type === "checkbox") {
                input.checked = false;
            } else {
                input.value = "";
            }
        });
    }

    function actualizarPreguntas() {
        form.querySelectorAll(".calidad-pregunta[data-visible-campo]").forEach((pregunta) => {
            const valor = valorDe(pregunta.dataset.visibleCampo);
            const valores = pregunta.dataset.visibleValores.split(",");
            const incluido = valor !== "" && valores.includes(valor);
            const visible = pregunta.dataset.visibleNegar === "1" ? valor !== "" && !incluido : incluido;
            if (!visible && !pregunta.hidden) {
                vaciar(pregunta);
            }
            pregunta.hidden = !visible;
        });
    }

    function actualizarEspecificar() {
        form.querySelectorAll(".calidad-especificar").forEach((bloque) => {
            const valor = valorDe(bloque.dataset.especificarCampo);
            const esperado = bloque.dataset.especificarValor;
            const visible = valor === "on" ? true : valor === esperado;
            if (!visible && !bloque.hidden) {
                vaciar(bloque);
            }
            bloque.hidden = !visible;
        });
    }

    function actualizar() {
        actualizarPreguntas();
        actualizarEspecificar();
    }

    // El primer botón submit del form es "Enviar" y el envío es irreversible:
    // Enter dentro de un campo no debe disparar el envío implícito.
    form.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && event.target.tagName === "INPUT") {
            event.preventDefault();
        }
    });

    // Evita un segundo POST por doble clic, que crearía otro envío inmutable.
    let enviando = false;
    form.addEventListener("submit", (event) => {
        if (enviando) {
            event.preventDefault();
            return;
        }
        enviando = true;
    });
    window.addEventListener("pageshow", () => {
        enviando = false;
    });

    form.addEventListener("change", actualizar);
    actualizar();
})();
