/* global L */
(() => {
    "use strict";
    function initialize() {
        document.querySelectorAll("[data-pin-editor]").forEach((root) => {
            if (root.dataset.initialized) return;
            root.dataset.initialized = "true";
            const latitude = document.getElementById(root.dataset.latitudeField);
            const longitude = document.getElementById(root.dataset.longitudeField);
            if (!latitude || !longitude || latitude.disabled || longitude.disabled) {
                root.hidden = true;
                return;
            }
            const alwaysVisible = root.dataset.alwaysVisible === "true";
            const start = root.querySelector("[data-pin-start]");
            const panel = root.querySelector("[data-pin-panel]");
            const status = root.querySelector("[data-pin-status]");
            const preview = document.getElementById(root.dataset.previewFrame);
            const addressFields = (root.dataset.addressFields || "").split(",").filter(Boolean).map(id => document.getElementById(id));
            const addressSnapshot = () => addressFields.map(field => field ? field.value : "").join("|");
            const originalAddress = addressSnapshot();
            let map, marker, original, generation = 0, edited = false;
            const coordinates = () => {
                if (!latitude.value.trim() || !longitude.value.trim()) return null;
                const lat = Number(latitude.value), lng = Number(longitude.value);
                return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? [lat, lng] : null;
            };
            function position(latlng, zoom = 18) {
                if (!marker) {
                    marker = L.marker(latlng, { draggable: true, title: "Ubicación del legajo" }).addTo(map);
                    marker.on("dragend", () => commitPosition(marker.getLatLng()));
                } else marker.setLatLng(latlng);
                map.invalidateSize({ pan: false });
                map.setView(latlng, zoom, { animate: false });
            }
            function commitPosition(latlng) {
                const lat = Number(latlng.lat), lng = Number(latlng.lng);
                if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
                    status.textContent = "El punto está fuera del rango válido. Elegí una ubicación dentro del mapa.";
                    return;
                }
                edited = true;
                generation += 1;
                latitude.value = lat.toFixed(6);
                longitude.value = lng.toFixed(6);
                latitude.dispatchEvent(new Event("input", { bubbles: true }));
                longitude.dispatchEvent(new Event("input", { bubbles: true }));
                status.textContent = "Coordenadas actualizadas. Guardá el formulario para confirmar la ubicación.";
            }
            async function openEditor(resolveAddress = true) {
                if (typeof L === "undefined") {
                    status.textContent = "No se pudo cargar el editor. Podés ingresar las coordenadas en los campos del formulario.";
                    return;
                }
                if (!original || panel.hidden) original = [latitude.value, longitude.value];
                edited = false;
                const currentGeneration = ++generation;
                panel.hidden = false;
                start.hidden = !alwaysVisible;
                if (preview) preview.hidden = true;
                if (!map) {
                    map = L.map(root.querySelector("[data-pin-map]"), { worldCopyJump: true });
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        maxZoom: 19,
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    }).addTo(map);
                }
                map.invalidateSize();
                const current = coordinates();
                position(current || [-38.4, -63.6], current ? 18 : 4);
                status.textContent = current ? "Arrastrá el pin para ajustar la ubicación." : "Acercá el mapa y colocá el pin en el centro, o arrastralo hasta la ubicación correcta.";
                const searchDraft = Boolean(root.dataset.searchUrl);
                const searchSaved = root.dataset.locationUrl && addressSnapshot() === originalAddress;
                if (resolveAddress && !current && (searchDraft || searchSaved)) {
                    const requestedAddress = addressSnapshot();
                    status.textContent = "Buscando el domicilio para ubicar el pin…";
                    try {
                        const options = { headers: { Accept: "application/json" } };
                        if (searchDraft) {
                            const body = new URLSearchParams();
                            addressFields.filter(Boolean).forEach(field => {
                                let value = field.value;
                                if (root.dataset.genericSearch === "true" && field.tagName === "SELECT") {
                                    value = field.value && field.selectedOptions.length ? field.selectedOptions[0].textContent.trim() : "";
                                }
                                body.append(field.name, value);
                            });
                            const csrf = latitude.form && latitude.form.querySelector("[name=csrfmiddlewaretoken]");
                            options.method = "POST";
                            options.headers["X-CSRFToken"] = csrf ? csrf.value : "";
                            options.body = body;
                        }
                        const response = await fetch(searchDraft ? root.dataset.searchUrl : root.dataset.locationUrl, options);
                        const result = await response.json();
                        if (generation !== currentGeneration || panel.hidden || edited || addressSnapshot() !== requestedAddress) return;
                        if (!response.ok) {
                            status.textContent = result.status === "invalid"
                                ? "Completá provincia, municipio, calle y altura válidos para buscar el domicilio."
                                : "No se pudo buscar el domicilio. Podés colocar el pin manualmente.";
                            return;
                        }
                        const lat = Number(result.lat), lng = Number(result.lon);
                        if (result.status === "located" && Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
                            position([lat, lng]);
                            commitPosition({ lat, lng });
                            status.textContent = "Coordenadas completadas desde el domicilio. Podés ajustar el pin; guardá el formulario para confirmar la ubicación.";
                        } else {
                            status.textContent = result.status === "ambiguous"
                                ? "El domicilio tiene varias coincidencias. Completá la dirección o colocá el pin manualmente."
                                : "No se encontró el domicilio. Revisá la dirección o colocá el pin manualmente.";
                        }
                    } catch (_) {
                        if (generation === currentGeneration) status.textContent = "No se pudo buscar el domicilio. Acercá el mapa y colocá el pin manualmente.";
                    }
                }
            }
            start.addEventListener("click", openEditor);
            root.addEventListener("pin:preview", openEditor);
            root.querySelector("[data-pin-center]").addEventListener("click", () => {
                const center = map.getCenter();
                position(center, map.getZoom());
                commitPosition(center);
            });
            root.querySelector("[data-pin-cancel]").addEventListener("click", () => {
                generation += 1;
                [latitude.value, longitude.value] = original;
                latitude.dispatchEvent(new Event("input", { bubbles: true }));
                longitude.dispatchEvent(new Event("input", { bubbles: true }));
                panel.hidden = !alwaysVisible;
                start.hidden = false;
                if (preview) preview.hidden = false;
                if (alwaysVisible && map) {
                    const current = coordinates();
                    position(current || [-38.4, -63.6], current ? 18 : 4);
                }
                status.textContent = "Ajuste descartado. Se conservaron las coordenadas anteriores.";
            });
            [latitude, longitude].forEach(field => field.addEventListener("change", () => {
                generation += 1;
                const current = coordinates();
                if (map && current && !panel.hidden) position(current);
            }));
            const section = root.closest ? root.closest(".collapse") : null;
            if (section && typeof window !== "undefined" && window.jQuery) {
                window.jQuery(section).on("shown.bs.collapse", () => { if (map) map.invalidateSize(); });
            }
            const form = latitude.form;
            if (form) form.addEventListener("reset", () => {
                generation += 1;
                panel.hidden = true;
                start.hidden = false;
                if (preview) preview.hidden = false;
            });
            if (alwaysVisible) openEditor(false);
        });
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
    else initialize();
})();
