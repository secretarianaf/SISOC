// Verificación contra RENAPER de un lote de carga masiva, por tandas.
// Pide una tanda por vez hasta que no queden personas pendientes y recarga la
// vista previa. Si RENAPER no responde, se detiene y ofrece reintentar.
(function () {
    "use strict";

    const panel = document.getElementById("renaper-verificacion");
    if (!panel) {
        return;
    }
    const url = panel.dataset.url;
    const total = Number(panel.dataset.total) || 1;
    const barra = panel.querySelector(".progress-bar");
    const texto = panel.querySelector("[data-renaper-texto]");
    const reintentar = panel.querySelector("[data-renaper-reintentar]");
    const csrf = document.querySelector("[name=csrfmiddlewaretoken]");

    function mostrarAvance(pendientes) {
        const hechas = Math.max(total - pendientes, 0);
        const porcentaje = Math.round((hechas / total) * 100);
        barra.style.width = porcentaje + "%";
        barra.setAttribute("aria-valuenow", String(porcentaje));
        texto.textContent = "Verificando con RENAPER: " + hechas + " de " + total + " personas.";
    }

    function detener(mensaje) {
        texto.textContent = mensaje;
        reintentar.classList.remove("d-none");
    }

    async function verificar() {
        reintentar.classList.add("d-none");
        try {
            for (;;) {
                const respuesta = await fetch(url, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrf ? csrf.value : "" },
                    credentials: "same-origin",
                });
                if (!respuesta.ok) {
                    detener("No se pudo continuar la verificación. Recargue la página.");
                    return;
                }
                const avance = await respuesta.json();
                mostrarAvance(avance.pendientes);
                if (avance.pendientes === 0) {
                    window.location.reload();
                    return;
                }
                if (avance.consultadas === avance.fallas) {
                    detener("RENAPER no está respondiendo. Puede reintentar en unos minutos.");
                    return;
                }
            }
        } catch (error) {
            detener("Se perdió la conexión durante la verificación. Puede reintentar.");
        }
    }

    reintentar.addEventListener("click", verificar);
    verificar();
})();
