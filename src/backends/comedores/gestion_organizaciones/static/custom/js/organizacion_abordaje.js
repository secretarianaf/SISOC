document.addEventListener("DOMContentLoaded", function () {
    const region = document.getElementById("id_region_abordaje");
    const subzona = document.getElementById("id_subzona_abordaje");
    const catalogo = document.getElementById("subzonas-abordaje-json");
    if (region && subzona && catalogo) {
        const opciones = JSON.parse(catalogo.textContent);
        region.addEventListener("change", function () {
            const seleccionada = subzona.value;
            subzona.replaceChildren(new Option("---------", ""));
            opciones.filter((item) => item.region_id && String(item.region_id) === region.value)
                .forEach((item) => subzona.add(new Option(item.nombre, String(item.id))));
            subzona.value = Array.from(subzona.options).some((item) => item.value === seleccionada)
                ? seleccionada : "";
            subzona.dispatchEvent(new Event("change", { bubbles: true }));
        });
    }
    const input = document.getElementById("id_asignaciones_territoriales");
    const codigos = document.getElementById("id_codigos_proyecto");
    const proyecto = document.getElementById("asignacion-proyecto");
    const territorial = document.getElementById("asignacion-territorial");
    const listado = document.getElementById("asignaciones-territoriales-listado");
    const error = document.getElementById("asignacion-territorial-error");
    if (!input || !codigos || !proyecto || !territorial || !listado) return;
    const header = document.querySelector('[data-toggle-section="abordaje"]');
    const section = document.getElementById("section-abordaje");
    header.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            header.click();
        }
    });
    new MutationObserver(() => header.setAttribute("aria-expanded", String(section.classList.contains("show"))))
        .observe(section, { attributes: true, attributeFilter: ["class"] });
    let asignaciones;
    try {
        const valor = JSON.parse(input.value || "[]");
        asignaciones = Array.isArray(valor) ? valor : [];
    } catch {
        asignaciones = [];
    }

    function actualizarProyectos() {
        const seleccionado = proyecto.value;
        const opciones = codigos.value.split(",").map((codigo) => codigo.trim()).filter(Boolean);
        proyecto.replaceChildren(new Option("Seleccionar proyecto", ""));
        opciones.forEach((codigo) => proyecto.add(new Option(codigo, codigo)));
        proyecto.value = seleccionado;
    }

    function renderizar() {
        input.value = JSON.stringify(asignaciones);
        listado.replaceChildren();
        asignaciones.forEach((item, indice) => {
            const fila = document.createElement("div");
            fila.className = "list-group-item d-flex justify-content-between align-items-center";
            const usuario = Array.from(territorial.options).find((opcion) => Number(opcion.value) === item.territorial);
            const texto = document.createElement("span");
            texto.textContent = item.proyecto + " — " + (usuario ? usuario.textContent : "Territorial no disponible");
            const quitar = document.createElement("button");
            quitar.type = "button";
            quitar.className = "btn btn-outline-danger btn-sm";
            quitar.textContent = "Quitar";
            quitar.setAttribute("aria-label", "Quitar asignación de " + item.proyecto);
            quitar.addEventListener("click", () => {
                asignaciones.splice(indice, 1);
                renderizar();
            });
            fila.append(texto, quitar);
            listado.append(fila);
        });
    }

    proyecto.addEventListener("focus", actualizarProyectos);
    codigos.addEventListener("change", actualizarProyectos);
    document.getElementById("agregar-asignacion-territorial").addEventListener("click", () => {
        const usuario = Number(territorial.value);
        if (!proyecto.value || !usuario) {
            error.textContent = "Seleccioná un Código de Proyecto y un Territorial.";
            error.classList.remove("d-none");
            return;
        }
        error.classList.add("d-none");
        if (!asignaciones.some((item) => item.proyecto === proyecto.value && item.territorial === usuario)) {
            asignaciones.push({ proyecto: proyecto.value, territorial: usuario });
            renderizar();
        }
    });
    actualizarProyectos();
    renderizar();
});
