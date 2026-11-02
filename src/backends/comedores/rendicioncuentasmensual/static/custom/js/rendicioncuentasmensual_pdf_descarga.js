// Descarga consolidada de la rendición: el PDF se genera en segundo plano
// (issue #2845). Se solicita, se consulta el estado y al estar listo se descarga.
document.addEventListener("DOMContentLoaded", function () {
    const INTERVALO_MS = 3000;
    const ESPERA_MAXIMA_MS = 15 * 60 * 1000;

    document.querySelectorAll(".js-pdf-descarga-form").forEach(function (form) {
        const button = form.querySelector("button[type='submit']");
        const idle = form.querySelector(".js-submit-idle");
        const spinner = form.querySelector(".js-submit-spinner");
        const mensaje = form.parentElement.querySelector(".js-pdf-descarga-mensaje");
        let inicio = 0;

        const setGenerando = function (generando) {
            button.disabled = generando;
            idle.classList.toggle("d-none", generando);
            spinner.classList.toggle("d-none", !generando);
        };

        const mostrar = function (texto, esError) {
            if (!mensaje) {
                return;
            }
            mensaje.textContent = texto || "";
            mensaje.classList.toggle("text-danger", Boolean(esError));
            mensaje.classList.toggle("text-muted", !esError);
        };

        const leerJson = function (response) {
            return response.json().catch(function () {
                return {};
            }).then(function (data) {
                if (!response.ok) {
                    throw new Error(data.mensaje || "No se pudo generar el PDF.");
                }
                return data;
            });
        };

        const procesar = function (data) {
            if (data.estado === "listo" && data.url_descarga) {
                setGenerando(false);
                mostrar("PDF listo. La descarga comienza en unos segundos.", false);
                window.location.href = data.url_descarga;
                return;
            }
            if (data.estado === "pendiente" || data.estado === "procesando") {
                if (Date.now() - inicio > ESPERA_MAXIMA_MS) {
                    throw new Error("La generación del PDF tardó demasiado. Intentá nuevamente.");
                }
                mostrar("Generando el PDF. Puede tardar unos minutos.", false);
                window.setTimeout(consultarEstado, INTERVALO_MS);
                return;
            }
            throw new Error(data.mensaje || "No se pudo generar el PDF.");
        };

        const fallar = function (error) {
            setGenerando(false);
            mostrar(error.message, true);
        };

        const consultarEstado = function () {
            fetch(form.dataset.estadoUrl, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then(leerJson)
                .then(procesar)
                .catch(fallar);
        };

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            inicio = Date.now();
            setGenerando(true);
            mostrar("", false);
            fetch(form.action, {
                method: "POST",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                body: new FormData(form),
            })
                .then(leerJson)
                .then(procesar)
                .catch(fallar);
        });
    });
});
