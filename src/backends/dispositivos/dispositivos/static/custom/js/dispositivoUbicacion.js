/* Previsualización local: solo Guardar dispositivo persiste los campos. */
document.addEventListener("DOMContentLoaded", () => {
    const field = (name) => document.getElementById(`id_${name}`);
    const provincia = field("provincia");
    const municipio = field("municipio");
    const localidad = field("localidad");
    const status = document.getElementById("dispositivo-mapa-estado");
    const frame = document.getElementById("dispositivo-mapa");
    const button = document.getElementById("dispositivo-mapa-buscar");
    if (!button || !provincia || !municipio || !localidad) return;

    function resetLocalidades() {
        localidad.replaceChildren(new Option("---------", ""));
    }
    let generation = 0;
    provincia.addEventListener("change", () => {
        generation += 1;
        resetLocalidades();
    });
    municipio.addEventListener("change", async () => {
        const requestGeneration = ++generation;
        const municipioId = municipio.value;
        resetLocalidades();
        if (!municipioId) return;
        try {
            const response = await fetch(`${window.ajaxLoadLocalidadesUrl}?municipio_id=${encodeURIComponent(municipioId)}`);
            if (!response.ok) throw new Error("localidades");
            const items = await response.json();
            if (generation !== requestGeneration) return;
            items.forEach((item) => localidad.add(new Option(item.nombre, item.id)));
        } catch (_) {
            if (generation === requestGeneration) {
                status.textContent = "No se pudieron cargar las localidades. Volvé a seleccionar el municipio para reintentar.";
            }
        }
    });
    const value = (name) => field(name).value.trim();
    const selectedName = (select) => select.value ? select.selectedOptions[0].textContent.trim() : "";
    function preview(event) {
        const lat = value("latitud");
        const lon = value("longitud");
        let query;
        if (lat || lon) {
            if (!lat || !lon || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon)) || Math.abs(Number(lat)) > 90 || Math.abs(Number(lon)) > 180) {
                status.textContent = "Completá ambas coordenadas válidas: latitud entre -90 y 90 y longitud entre -180 y 180.";
                return;
            }
            query = `${lat},${lon}`;
        } else {
            if (!value("calle") || !value("altura") || !provincia.value || !municipio.value) {
                status.textContent = "Completá provincia, municipio, calle y altura para previsualizar el domicilio.";
                return;
            }
            query = [`${value("calle")} ${value("altura")}`, selectedName(localidad), selectedName(municipio), selectedName(provincia), "Argentina"].filter(Boolean).join(", ");
        }
        frame.src = `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
        status.textContent = "Ubicación previsualizada. Guardá el dispositivo para confirmar los datos.";
        if (event && event.type === "click") {
            const editor = document.querySelector("[data-pin-editor]");
            if (editor) editor.dispatchEvent(new Event("pin:preview"));
        }
    }
    button.addEventListener("click", preview);
    if ((value("latitud") && value("longitud")) || (value("calle") && municipio.value && provincia.value)) preview();
});
