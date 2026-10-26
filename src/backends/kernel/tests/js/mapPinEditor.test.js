const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");
const source = readFileSync(resolve(__dirname, "../../static/custom/js/mapPinEditor.js"), "utf8");
function setup({ lat = "-34.9", lng = "-57.9", locationUrl = "", fetch, searchUrl = "", disabled = false, library = true } = {}) {
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
    const root = { handlers: {}, addEventListener(name, cb) { this.handlers[name] = cb; }, dataset: { latitudeField: "latitude", longitudeField: "longitude", previewFrame: "preview", locationUrl, searchUrl, addressFields: "calle" }, querySelector: key => nodes[key.slice(10, -1)] };
    const views = [];
    const map = { setView(position, zoom) { views.push({ position, zoom }); }, invalidateSize() {}, getCenter: () => ({ lat: -35, lng: -58 }), getZoom: () => 12 };
    const marker = { on(name, handler) { this[name] = handler; }, addTo() { return this; }, setLatLng(value) { this.position = value; }, getLatLng() { return this.position; } };
    const context = {
        document: { readyState: "complete", querySelectorAll: () => [root], getElementById: id => fields[id] },
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
