const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");
const source = readFileSync(resolve(__dirname, "../../static/custom/js/dispositivoUbicacion.js"), "utf8");
function setup(values = {}, fetch = async () => ({ ok: true, json: async () => [] })) {
    const nodes = {};
    for (const name of ["provincia", "municipio", "localidad", "calle", "altura", "latitud", "longitud"]) {
        nodes[`id_${name}`] = {
            value: values[name] || "", handlers: {},
            selectedOptions: [{ textContent: values[name] || "" }],
            addEventListener(event, callback) { this.handlers[event] = callback; },
            replaceChildren(...items) { this.items = items; this.value = ""; },
            add(item) { this.items.push(item); },
        };
    }
    nodes["dispositivo-mapa-estado"] = {};
    nodes["dispositivo-mapa"] = { src: "original" };
    nodes["dispositivo-mapa-buscar"] = { addEventListener(_, cb) { this.click = cb; } };
    runInNewContext(source, {
        document: { querySelector: () => null, getElementById: id => nodes[id], addEventListener: (_, cb) => cb() },
        window: { ajaxLoadLocalidadesUrl: "/localidades/" }, fetch,
        Option: function(text, value) { this.text = text; this.value = value; },
    });
    return nodes;
}
test("prioriza coordenadas incluso cero y no modifica domicilio", () => {
    const nodes = setup({ latitud: "0", longitud: "0", calle: "Calle" });
    assert.match(nodes["dispositivo-mapa"].src, /q=0%2C0&output=embed/);
    assert.equal(nodes.id_calle.value, "Calle");
});
test("usa domicilio cuando faltan ambas coordenadas", () => {
    const nodes = setup({ provincia: "Buenos Aires", municipio: "La Plata", localidad: "Tolosa", calle: "Calle 1", altura: "123" });
    assert.match(decodeURIComponent(nodes["dispositivo-mapa"].src), /Calle 1 123, Tolosa, La Plata, Buenos Aires, Argentina/);
});
test("rechaza coordenadas parciales o fuera de rango sin cambiar mapa", () => {
    for (const values of [{ latitud: "-34" }, { latitud: "91", longitud: "0" }, { latitud: "NaN", longitud: "0" }]) {
        const nodes = setup(values);
        nodes["dispositivo-mapa-buscar"].click();
        assert.equal(nodes["dispositivo-mapa"].src, "original");
        assert.match(nodes["dispositivo-mapa-estado"].textContent, /ambas coordenadas/);
    }
});
test("domicilio incompleto no cambia mapa", () => {
    const nodes = setup();
    nodes["dispositivo-mapa-buscar"].click();
    assert.equal(nodes["dispositivo-mapa"].src, "original");
    assert.match(nodes["dispositivo-mapa-estado"].textContent, /Completá provincia/);
});
test("descarta localidades de un municipio anterior", async () => {
    let resolveResponse;
    const nodes = setup({}, () => new Promise(resolve => { resolveResponse = resolve; }));
    nodes.id_municipio.value = "1";
    const pending = nodes.id_municipio.handlers.change();
    nodes.id_provincia.handlers.change();
    resolveResponse({ ok: true, json: async () => [{ id: 1, nombre: "Anterior" }] });
    await pending;
    assert.equal(nodes.id_localidad.items.length, 1);
});
test("carga localidades del municipio y avisa si falla", async () => {
    const nodes = setup({}, async () => ({ ok: true, json: async () => [{ id: 7, nombre: "Localidad" }] }));
    nodes.id_municipio.value = "1";
    await nodes.id_municipio.handlers.change();
    assert.equal(nodes.id_localidad.items[1].value, 7);
    const failed = setup({}, async () => ({ ok: false }));
    failed.id_municipio.value = "1";
    await failed.id_municipio.handlers.change();
    assert.match(failed["dispositivo-mapa-estado"].textContent, /No se pudieron cargar/);
});
