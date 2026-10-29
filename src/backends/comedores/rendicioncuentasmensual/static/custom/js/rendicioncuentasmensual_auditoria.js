document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("auditoria-form");
    if (form) {
        const genera = form.querySelector("[name='genera_acta_auditoria']");
        const resultado = form.querySelector("[name='resultado']");
        const opciones = form.querySelectorAll("[name='rendiciones_incluidas']");
        const guardar = document.getElementById("auditoria-guardar");
        const ayudaGuardar = document.getElementById("auditoria-guardar-ayuda");
        const iconoCierre = document.getElementById("auditoria-cierre-icono");
        const mostrar = function (id, visible) {
            const container = document.getElementById(id);
            container.hidden = !visible;
            container.querySelectorAll("input, select, textarea").forEach(function (input) {
                input.disabled = !visible || input.dataset.inclusionObligatoria === "true";
            });
        };
        const actualizar = function () {
            const conActa = genera.value === "True";
            const conObservaciones = conActa && resultado.value === "finalizada_con_observaciones";
            genera.required = true;
            guardar.textContent = "Guardar y cerrar Auditoría";
            ayudaGuardar.textContent = "Al guardar la decisión sobre el acta, la gestión de esta rendición se cierra.";
            iconoCierre.hidden = false;
            mostrar("campos-acta", conActa);
            mostrar("campos-observaciones", conObservaciones);
            resultado.required = conActa;
            form.querySelector("[name='observaciones']").required = conObservaciones;
            const seleccionadas = new Set(Array.from(opciones).filter(input => input.checked).map(input => input.value));
            document.querySelectorAll(".js-resumen-rendicion").forEach(function (resumen) {
                resumen.hidden = resumen.dataset.actual !== "true" && (!conActa || !seleccionadas.has(resumen.dataset.rendicion));
            });
        };
        genera.addEventListener("change", actualizar);
        resultado.addEventListener("change", actualizar);
        opciones.forEach(input => input.addEventListener("change", actualizar));
        actualizar();
    }
    const filtro = document.getElementById("id_filtro");
    const busqueda = document.getElementById("id_busqueda");
    const ayuda = document.getElementById("ayuda-busqueda-auditoria");
    if (filtro && busqueda && ayuda) {
        const indicaciones = {
            proyecto: ["Código o nombre del proyecto", "Buscá por el código o el nombre del proyecto."],
            organizacion: ["Nombre de la organización", "Buscá por el nombre de la organización."],
            periodo: ["MM/AAAA o DD/MM/AAAA", "Ingresá un mes, una fecha o un año. Se incluyen los períodos que lo contengan."],
        };
        const actualizarAyuda = function () {
            const textos = indicaciones[filtro.value] || indicaciones.proyecto;
            busqueda.placeholder = textos[0];
            ayuda.textContent = textos[1];
        };
        filtro.addEventListener("change", actualizarAyuda);
        actualizarAyuda();
    }
});
