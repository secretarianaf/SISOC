const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");
const source = readFileSync(resolve(__dirname, "../../static/custom/js/mapPinEditor.js"), "utf8");
function setup({ lat = "-34.9", lng = "-57.9", locationUrl = "", fetch, searchUrl = "", disabled = false, library = true, alwaysVisible = false } = {}) {
    const element = (value = "") => ({
        value, hidden: false, handlers: {}, disabled: false, events: [],
        addEventListener(name, callback) { this.handlers[name] = callback; },
        dispatchEvent(event) { this.events.push(event.type); },
    });
    const fields = { latitude: element(lat), longitude: element(lng), preview: element(), calle: element("Calle original") };
    fields.latitude.disabled = disabled;
    fields.latitude.form = element();
    fields.latitude.form.querySelector = () => ({ value: "csrf-test" });
    fields.calle.name = "calle";
    const nodes = Object.fromEntries(["start", "panel", "status", "map", "center", "cancel"].map(name => [name, element()]));
    nodes.panel.hidden = true;
    const root = { handlers: {}, addEventListener(name, cb) { this.handlers[name] = cb; }, dataset: { alwaysVisible: String(alwaysVisible), latitudeField: "latitude", longitudeField: "longitude", previewFrame: "preview", locationUrl, searchUrl, addressFields: "calle" }, querySelector: key => nodes[key.slice(10, -1)] };
    const views = [];
    const map = { setView(position, zoom, options) { views.push({ position, zoom, options }); }, invalidateSize() {}, getCenter: () => ({ lat: -35, lng: -58 }), getZoom: () => 12 };
    const marker = { on(name, handler) { this[name] = handler; }, addTo() { return this; }, setLatLng(value) { this.position = value; }, getLatLng() { return this.position; } };
    const context = {
        document: { readyState: "complete", addEventListener() {}, querySelectorAll: () => [root], getElementById: id => fields[id] },
        URLSearchParams,
        Event: function(type) { this.type = type; }, fetch: fetch || (() => { throw new Error("No debe consultar red"); }),
    };
    if (library) context.L = { map: () => map, tileLayer: () => ({ addTo() {} }), marker: position => { marker.position = position; return marker; } };
    runInNewContext(source, context);
    return { fields, nodes, root, views, marker, map };
}
test("abrir editor no modifica coordenadas y arrastrar actualiza solo coordenadas", async () => {
    const { fields, nodes, marker } = setup();
    await nodes.start.handlers.click();
    assert.equal(fields.latitude.value, "-34.9");
    assert.equal(fields.preview.hidden, true);
    marker.position = { lat: -34.12345678, lng: -58.12345678 };
    marker.dragend();
    assert.equal(fields.latitude.value, "-34.123457");
    assert.equal(fields.longitude.value, "-58.123457");
    assert.equal(fields.calle.value, "Calle original");
    assert.match(nodes.status.textContent, /Guardá el formulario/);
});
test("descartar restaura coordenadas previas incluso después de varios movimientos", async () => {
    const { fields, nodes, marker } = setup();
    await nodes.start.handlers.click();
    marker.position = { lat: 1, lng: 2 };
    marker.dragend();
    nodes.cancel.handlers.click();
    assert.equal(fields.latitude.value, "-34.9");
    assert.equal(fields.longitude.value, "-57.9");
    assert.equal(fields.preview.hidden, false);
    assert.equal(nodes.panel.hidden, true);
});
test("coordenadas cero se respetan sin consultar domicilio", async () => {
    const { nodes, views } = setup({ lat: "0", lng: "0", locationUrl: "/ubicacion/" });
    await nodes.start.handlers.click();
    assert.equal(views[0].position[0], 0);
    assert.equal(views[0].position[1], 0);
});
test("coordenadas se pueden colocar en centro sin arrastre", async () => {
    const { fields, nodes } = setup({ lat: "", lng: "" });
    await nodes.start.handlers.click();
    assert.equal(fields.latitude.value, "");
    nodes.center.handlers.click();
    assert.equal(fields.latitude.value, "-35.000000");
    assert.equal(fields.longitude.value, "-58.000000");
});
test("resolución de domicilio completa los campos y descartar recupera valores anteriores", async () => {
    const { fields, nodes, views } = setup({ lat: "", lng: "", locationUrl: "/ubicacion/", fetch: async () => ({ ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) }) });
    await nodes.start.handlers.click();
    assert.equal(views.at(-1).position[0], -34);
    assert.equal(fields.latitude.value, "-34.000000");
    assert.equal(fields.longitude.value, "-58.000000");
    nodes.cancel.handlers.click();
    assert.equal(fields.latitude.value, "");
    assert.equal(fields.longitude.value, "");
});
test("respuesta tardía no revierte un pin movido ni un ajuste descartado", async () => {
    for (const cancel of [false, true]) {
        let resolveResponse;
        const { fields, nodes, marker, views } = setup({ lat: "", lng: "", locationUrl: "/ubicacion/", fetch: () => new Promise(resolve => { resolveResponse = resolve; }) });
        const pending = nodes.start.handlers.click();
        if (cancel) nodes.cancel.handlers.click();
        else { marker.position = { lat: 1, lng: 2 }; marker.dragend(); }
        resolveResponse({ ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) });
        await pending;
        assert.equal(views.length, 1);
        assert.equal(fields.latitude.value, cancel ? "" : "1.000000");
    }
});
test("domicilio modificado no usa una ubicación guardada vieja", async () => {
    const { fields, nodes } = setup({ lat: "", lng: "", locationUrl: "/ubicacion/" });
    fields.calle.value = "Nueva calle";
    await nodes.start.handlers.click();
    assert.equal(fields.latitude.value, "");
});
test("fallo de búsqueda permite seleccionar ubicación manual", async () => {
    const { fields, nodes } = setup({ lat: "", lng: "", locationUrl: "/ubicacion/", fetch: async () => ({ ok: false, json: async () => ({}) }) });
    await nodes.start.handlers.click();
    assert.match(nodes.status.textContent, /manualmente/);
    nodes.center.handlers.click();
    assert.equal(fields.latitude.value, "-35.000000");
});
test("sin librería o con campos deshabilitados no altera ubicación", async () => {
    const missing = setup({ library: false });
    await missing.nodes.start.handlers.click();
    assert.match(missing.nodes.status.textContent, /No se pudo cargar/);
    assert.equal(missing.fields.latitude.value, "-34.9");
    const disabled = setup({ disabled: true });
    assert.equal(disabled.root.hidden, true);
});
test("reset cierra el editor y deja que el formulario restaure sus valores", async () => {
    const { fields, nodes } = setup();
    await nodes.start.handlers.click();
    fields.latitude.form.handlers.reset();
    assert.equal(nodes.panel.hidden, true);
    assert.equal(fields.preview.hidden, false);
});


test("domicilio nuevo se busca sin guardar y después permite ajustar pin", async () => {
    let request;
    const { fields, nodes, marker, views } = setup({ lat: "", lng: "", searchUrl: "/previsualizar/", fetch: async (url, options) => {
        request = { url, options };
        return { ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) };
    } });
    fields.calle.value = "Nueva calle";
    await nodes.start.handlers.click();
    assert.equal(request.url, "/previsualizar/");
    assert.equal(request.options.method, "POST");
    assert.equal(request.options.headers["X-CSRFToken"], "csrf-test");
    assert.equal(request.options.body.get("calle"), "Nueva calle");
    assert.equal(views.at(-1).position[0], -34);
    assert.equal(fields.latitude.value, "-34.000000");
    assert.equal(fields.longitude.value, "-58.000000");
    marker.position = { lat: -34.1, lng: -58.1 };
    marker.dragend();
    assert.equal(fields.latitude.value, "-34.100000");
    assert.equal(fields.calle.value, "Nueva calle");
});
test("un domicilio que cambia durante la búsqueda descarta la respuesta", async () => {
    let resolveResponse;
    const { fields, nodes, views } = setup({ lat: "", lng: "", searchUrl: "/previsualizar/", fetch: () => new Promise(resolve => { resolveResponse = resolve; }) });
    const pending = nodes.start.handlers.click();
    fields.calle.value = "Otra calle";
    resolveResponse({ ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) });
    await pending;
    assert.equal(views.length, 1);
});
test("domicilio inválido o ambiguo avisa sin completar coordenadas", async () => {
    for (const status of ["invalid", "ambiguous", "not_found"]) {
        const { fields, nodes } = setup({ lat: "", lng: "", searchUrl: "/previsualizar/", fetch: async () => ({ ok: status !== "invalid", json: async () => ({ status }) }) });
        await nodes.start.handlers.click();
        assert.equal(fields.latitude.value, "");
        assert.match(nodes.status.textContent, /Completá|varias coincidencias|No se encontró/);
    }
});

test("búsqueda compartida envía nombre geográfico seleccionado en vez de ID", async () => {
    let body;
    const { fields, nodes, root } = setup({ lat: "", lng: "", searchUrl: "/previsualizar/", fetch: async (_, options) => {
        body = options.body;
        return { ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) };
    } });
    root.dataset.genericSearch = "true";
    fields.calle.name = "provincia";
    fields.calle.tagName = "SELECT";
    fields.calle.value = "12";
    fields.calle.selectedOptions = [{ textContent: "Buenos Aires" }];
    await nodes.start.handlers.click();
    assert.equal(body.get("provincia"), "Buenos Aires");
});


test("mapa visible por defecto sin buscar ni completar campos al cargar", () => {
    const { fields, nodes, views } = setup({ lat: "", lng: "", searchUrl: "/buscar/", alwaysVisible: true });
    assert.equal(nodes.panel.hidden, false);
    assert.equal(nodes.start.hidden, false);
    assert.equal(views.length, 1);
    assert.equal(fields.latitude.value, "");
    assert.equal(fields.longitude.value, "");
});
test("descartar mantiene mapa visible y restaura las coordenadas", () => {
    const { fields, nodes, marker } = setup({ alwaysVisible: true });
    marker.position = { lat: 1, lng: 2 };
    marker.dragend();
    nodes.cancel.handlers.click();
    assert.equal(nodes.panel.hidden, false);
    assert.equal(nodes.start.hidden, false);
    assert.equal(fields.latitude.value, "-34.9");
    assert.equal(fields.longitude.value, "-57.9");
});


test("buscar dirección centra con zoom de calle sin animación pendiente", async () => {
    const { nodes, views, map } = setup({ lat: "", lng: "", searchUrl: "/buscar/", alwaysVisible: true, fetch: async () => ({ ok: true, json: async () => ({ status: "located", lat: -34.123456, lon: -58.123456 }) }) });
    let applied;
    map.setView = (position, zoom, options) => {
        // Leaflet puede ignorar otro zoom animado mientras termina el anterior.
        if (options && options.animate === false) applied = { position, zoom };
    };
    await nodes.start.handlers.click();
    assert.equal(views[0].zoom, 4);
    assert.equal(applied.position[0], -34.123456);
    assert.equal(applied.position[1], -58.123456);
    assert.equal(applied.zoom, 18);
});


test("desmontar el editor libera el mapa y descarta búsquedas pendientes", async () => {
    let resolveResponse;
    const { nodes, root, map, fields } = setup({ lat: "", lng: "", searchUrl: "/buscar/", fetch: () => new Promise(resolve => { resolveResponse = resolve; }) });
    map.remove = () => { map.removed = true; };
    const pending = nodes.start.handlers.click();
    root.handlers["pin:destroy"]();
    resolveResponse({ ok: true, json: async () => ({ status: "located", lat: -34, lon: -58 }) });
    await pending;
    assert.equal(map.removed, true);
    assert.equal(root.dataset.initialized, undefined);
    assert.equal(fields.latitude.value, "");
});


test("buscar otra dirección reemplaza el punto anterior solo al confirmar búsqueda", async () => {
    const { fields, nodes, root } = setup({ alwaysVisible: true, searchUrl: "/buscar/", fetch: async () => ({ ok: true, json: async () => ({ status: "located", lat: -35, lon: -59 }) }) });
    root.dataset.genericSearch = "true";
    fields.calle.value = "Otra dirección";
    await nodes.start.handlers.click();
    assert.equal(fields.latitude.value, "-35.000000");
    assert.equal(fields.longitude.value, "-59.000000");
    nodes.cancel.handlers.click();
    assert.equal(fields.latitude.value, "-34.9");
    assert.equal(fields.longitude.value, "-57.9");
});

test("dirección ambigua acerca el mapa sin completar coordenadas hasta confirmar el pin", async () => {
    const { fields, nodes, views } = setup({ lat: "", lng: "", searchUrl: "/preview/", fetch: async () => ({ ok: true, json: async () => ({ status: "ambiguous", suggestion: { lat: -34.91, lon: -57.96 } }) }) });
    await nodes.start.handlers.click();
    assert.equal(views.at(-1).position[0], -34.91);
    assert.equal(views.at(-1).zoom, 15);
    assert.equal(fields.latitude.value, "");
    assert.equal(fields.longitude.value, "");
    assert.match(nodes.status.textContent, /zona aproximada/);
    nodes.center.handlers.click();
    assert.equal(fields.latitude.value, "-35.000000");
});
