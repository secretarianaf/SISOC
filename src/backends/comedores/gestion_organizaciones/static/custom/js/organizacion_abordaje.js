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
    // Los territoriales por proyecto se cargan en cada fila de Proyectos
    // (organizacion_form.html, #2745).
    const header = document.querySelector('[data-toggle-section="abordaje"]');
    const section = document.getElementById("section-abordaje");
    if (!header || !section) return;
    header.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            header.click();
        }
    });
    new MutationObserver(() => header.setAttribute("aria-expanded", String(section.classList.contains("show"))))
        .observe(section, { attributes: true, attributeFilter: ["class"] });
});
