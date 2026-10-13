/* global L */
(() => {
    "use strict";
    const container = document.getElementById("dispositivos-map");
    const status = document.getElementById("map-status");
    const fitButton = document.getElementById("map-fit");
    if (!container) return;
    if (typeof L === "undefined") {
        status.textContent = "No se pudo cargar el mapa. Consultá las direcciones en la tabla.";
        return;
    }
    const devices = JSON.parse(document.getElementById("map-devices").textContent);
    const map = L.map(container).setView([-38.4, -63.6], 4);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    const markers = L.featureGroup().addTo(map);
    const markersByDevice = new Map();
    const table = document.getElementById("map-devices-table");
    const stateFilters = JSON.parse(document.getElementById("map-location-filters").textContent);
    const filterCount = document.getElementById("map-filter-count");
    const emptyRow = document.getElementById("map-filter-empty");
    const pagination = document.getElementById("map-pagination");
    const paginationPages = document.getElementById("map-pagination-pages");
    const pageSize = 15;
    let currentPage = 1;
    let filteredDevices = devices;
    let paginationSignature = "";
    const locations = new Map(devices.map(device => [String(device.id), "pending"]));
    const initialDevice = container.dataset.focusDevice;
    let userSelected = false;
    let selectedRow = null;
    const selectRow = (id) => {
        const index = filteredDevices.findIndex(device => String(device.id) === String(id));
        if (index >= 0 && currentPage !== Math.floor(index / pageSize) + 1) {
            currentPage = Math.floor(index / pageSize) + 1;
            applyFilters();
        }
        if (selectedRow) selectedRow.classList.remove("table-active");
        selectedRow = document.getElementById(`map-device-${id}`);
        if (selectedRow) selectedRow.classList.add("table-active");
    };
    const focusDevice = (id) => {
        const marker = markersByDevice.get(String(id));
        if (!marker || !markers.hasLayer(marker)) return;
        userSelected = true;
        selectRow(id);
        map.setView(marker.getLatLng(), 16);
        marker.openPopup();
        container.scrollIntoView({ behavior: "smooth", block: "center" });
    };
    table.addEventListener("click", (event) => {
        const button = event.target.closest("[data-map-focus]");
        if (button) {
            if (!button.disabled) focusDevice(button.dataset.mapFocus);
            return;
        }
    });
    map.on("dragstart", () => { userSelected = true; });
    const deviceIcon = L.divIcon({
        className: "dispositivo-map-marker", iconSize: [20, 20], iconAnchor: [10, 10],
    });
    const fit = () => {
        if (markers.getLayers().length) map.fitBounds(markers.getBounds(), { padding: [30, 30], maxZoom: 14 });
    };
    fitButton.addEventListener("click", () => {
        userSelected = true;
        fit();
    });
    const autoFit = () => { if (!userSelected) fit(); };
    const renderPagination = (pageCount) => {
        pagination.hidden = pageCount <= 1;
        const signature = `${currentPage}/${pageCount}`;
        if (signature === paginationSignature) return;
        paginationSignature = signature;
        paginationPages.replaceChildren();
        const addPage = (label, page, disabled = false, active = false) => {
            const item = document.createElement("li");
            item.className = `page-item${disabled ? " disabled" : ""}${active ? " active" : ""}`;
            const button = document.createElement("button");
            button.type = "button";
            button.className = "page-link";
            button.textContent = label;
            button.disabled = disabled || active;
            if (active) button.setAttribute("aria-current", "page");
            button.addEventListener("click", () => {
                currentPage = page;
                applyFilters();
            });
            item.append(button);
            paginationPages.append(item);
        };
        addPage("Volver", currentPage - 1, currentPage === 1);
        let previous = 0;
        for (let page = 1; page <= pageCount; page += 1) {
            if (page !== 1 && page !== pageCount && Math.abs(page - currentPage) > 2) continue;
            if (previous && page - previous > 1) addPage("…", currentPage, true);
            addPage(String(page), page, false, page === currentPage);
            previous = page;
        }
        addPage("Continuar", currentPage + 1, currentPage === pageCount);
    };
    const applyFilters = () => {
        filteredDevices = devices.filter(device =>
            stateFilters.every(filter => filter.op === "ne"
                ? locations.get(String(device.id)) !== filter.value
                : locations.get(String(device.id)) === filter.value)
        );
        const matchedIds = new Set(filteredDevices.map(device => String(device.id)));
        const pageCount = Math.max(1, Math.ceil(filteredDevices.length / pageSize));
        currentPage = Math.min(currentPage, pageCount);
        const offset = (currentPage - 1) * pageSize;
        const pageIds = new Set(filteredDevices.slice(offset, offset + pageSize).map(device => String(device.id)));
        for (const device of devices) {
            const id = String(device.id);
            document.getElementById(`map-device-${id}`).hidden = !pageIds.has(id);
            const marker = markersByDevice.get(id);
            if (marker) {
                if (matchedIds.has(id) && !markers.hasLayer(marker)) markers.addLayer(marker);
                if (!matchedIds.has(id) && markers.hasLayer(marker)) markers.removeLayer(marker);
            }
        }
        if (selectedRow && !matchedIds.has(selectedRow.dataset.deviceId)) {
            selectedRow.classList.remove("table-active");
            selectedRow = null;
            map.closePopup();
        }
        if (emptyRow) emptyRow.hidden = filteredDevices.length > 0;
        fitButton.disabled = markers.getLayers().length === 0;
        filterCount.textContent = filteredDevices.length
            ? `Mostrando ${offset + 1}–${Math.min(offset + pageSize, filteredDevices.length)} de ${filteredDevices.length} dispositivos`
            : "No se encontraron dispositivos";
        renderPagination(pageCount);
    };
    applyFilters();
    let located = 0;
    let processed = 0;
    let reused = 0;
    let unavailable = false;
    const labels = {
        located: "Ubicado", ambiguous: "Dirección ambigua", not_found: "Sin coincidencia",
        unavailable: "Servicio no disponible",
    };
    async function locateDevices() {
        const orderedDevices = [...devices.filter(device => device.location), ...devices.filter(device => !device.location)];
        for (const device of orderedDevices) {
            let result = device.location || { status: "unavailable" };
            if (device.location) reused += 1;
            if (!device.location && !unavailable) {
                try {
                    const response = await fetch(device.location_url, {
                        credentials: "same-origin", signal: AbortSignal.timeout(20000),
                    });
                    if (response.ok) result = await response.json();
                } catch (_) { /* El listado conserva la dirección aunque falle el servicio. */ }
            }
            if (result.status === "unavailable") unavailable = true;
            locations.set(String(device.id), result.status);
            if (result.status === "located") {
                const popup = document.createElement("div");
                const title = document.createElement("strong");
                title.textContent = device.name;
                const address = document.createElement("p");
                address.textContent = device.address;
                const type = document.createElement("p");
                type.textContent = device.type;
                const link = document.createElement("a");
                link.href = device.detail_url;
                link.textContent = "Ver detalle";
                link.className = "btn btn-ver";
                const representative = document.createElement("p");
                representative.textContent = `Representante: ${device.representative || "Sin datos"}`;
                const phone = document.createElement("p");
                phone.textContent = `Teléfono: ${device.phone || "Sin datos"}`;
                popup.append(title, address, type, representative, phone, link);
                const marker = L.marker([result.lat, result.lon], { title: device.name, icon: deviceIcon }).bindPopup(popup).addTo(markers);
                markersByDevice.set(String(device.id), marker);
                marker.on("popupopen", () => {
                    userSelected = true;
                    selectRow(device.id);
                });
                const row = document.getElementById(`map-device-${device.id}`);
                const button = row.querySelector("[data-map-focus]");
                button.disabled = false;
                button.title = `Ver ${device.name} en el mapa`;
                located += 1;
                fitButton.disabled = false;
            }
            applyFilters();
            if (located === 1 && result.status === "located") autoFit();
            if (String(device.id) === initialDevice && result.status === "located") focusDevice(device.id);
            processed += 1;
            const label = labels[result.status] || "Pendiente";
            document.getElementById(`location-status-${device.id}`).textContent = label;
            if (result.status !== "located") {
                document.querySelector(`[data-map-focus="${device.id}"]`).title = label;
            }
            status.textContent = `${located} ubicados · ${reused} guardados · ${processed - located} sin ubicar · ${processed}/${devices.length} revisados`;
            if (processed % 20 === 0) autoFit();
        }
        autoFit();
        if (!devices.length) status.textContent = "No hay dispositivos para mostrar con los filtros seleccionados.";
        if (unavailable) status.textContent += ". No se pudo consultar el servicio de ubicación. Volvé a intentar recargando la página.";
    }
    locateDevices();
})();
