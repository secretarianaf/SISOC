/* node --test src/backends/dispositivos/dispositivos/tests/js/dispositivosMap.test.js */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../static/custom/js/dispositivosMap.js'), 'utf8');

function setup(count = 2, initialDevice = "", stateFilters = [], savedIds = []) {
    const handlers = {};
    const requests = [];
    const layers = [];
    const views = [];
    let fits = 0;
    let scrolls = 0;
    const nodes = {};
    const element = () => ({
        children: [], handlers: {},
        append(...children) { this.children.push(...children); },
        replaceChildren() { this.children = []; },
        setAttribute() {},
        addEventListener(name, cb) { this.handlers[name] = cb; },
    });
    nodes['map-pagination'] = element();
    nodes['map-pagination-pages'] = element();
    const devices = Array.from({ length: count }, (_, i) => ({ id: i + 1, location: savedIds.includes(i + 1) ? { status: 'located', lat: -34.9, lon: -57.9 } : null, province_id: i + 1, province: `Province ${i + 1}`, representative: `Representante ${i + 1}`, phone: '221 5550001', name: `Device ${i + 1}`, address: 'Address', type: 'Refugio', detail_url: `/devices/${i + 1}/`, location_url: `/locations/${i + 1}/` }));
    for (const device of devices) {
        const classes = new Set();
        const button = { disabled: true, dataset: { mapFocus: String(device.id) } };
        const row = { dataset: { deviceId: String(device.id) }, querySelector: () => button, classList: { add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c) } };
        nodes[`map-device-${device.id}`] = row;
        nodes[`button-${device.id}`] = button;
        nodes[`location-status-${device.id}`] = {};
    }
    nodes['dispositivos-map'] = { dataset: { focusDevice: initialDevice }, scrollIntoView: () => { scrolls += 1; } };
    nodes['map-status'] = {};
    nodes['map-filter-count'] = {};
    nodes['map-filter-empty'] = { hidden: true };
    nodes['map-fit'] = { disabled: true, addEventListener: (_, cb) => { handlers.fit = cb; } };
    nodes['map-devices-table'] = { addEventListener: (_, cb) => { handlers.click = cb; } };
    nodes['map-devices'] = { textContent: JSON.stringify(devices) };
    nodes['map-location-filters'] = { textContent: JSON.stringify(stateFilters) };
    const map = { setView(position, zoom) { views.push({ position, zoom }); return this; }, fitBounds() { fits += 1; }, closePopup() {}, on(name, cb) { handlers[name] = cb; } };
    const L = {
        map: () => map,
        tileLayer: () => ({ addTo() {} }),
        featureGroup: () => ({
            addTo() { return this; }, getLayers: () => layers, getBounds: () => ({}),
            hasLayer: marker => layers.includes(marker),
            addLayer: marker => { layers.push(marker); },
            removeLayer: marker => { const index = layers.indexOf(marker); if (index !== -1) layers.splice(index, 1); },
        }),
        divIcon: () => ({}),
        marker(position) {
            return {
                position, opened: false, bindPopup(popup) { this.popup = popup; return this; },
                addTo(group) { group.addLayer(this); return this; },
                on(_, cb) { this.popupOpen = cb; },
                getLatLng() { this.position.lat = this.position[0]; this.position.lng = this.position[1]; return this.position; },
                openPopup() { this.opened = true; this.popupOpen(); },
            };
        },
    };
    runInNewContext(source, {
        L, AbortSignal: { timeout: () => null },
        document: {
            getElementById: id => nodes[id],
            querySelector: selector => nodes[`button-${selector.match(/"(\d+)"/)[1]}`],
            createElement: element,
        },
        fetch: () => new Promise(resolveResponse => { requests.push(resolveResponse); }),
    });
    async function finish(index, result) {
        requests[index]({ ok: true, json: async () => result });
        for (let i = 0; i < 12; i += 1) await Promise.resolve();
    }
    function select(id, byRow = false) {
        const row = nodes[`map-device-${id}`];
        const button = nodes[`button-${id}`];
        handlers.click({ target: { closest(selector) {
            if (selector === '[data-map-focus]') return byRow ? null : button;
            if (selector === '[data-device-id]') return row;
            return null;
        } } });
    }
    function page(label) {
        const item = nodes['map-pagination-pages'].children.find(item => item.children[0].textContent === label);
        const button = item.children[0];
        if (!button.disabled) button.handlers.click();
    }
    return { requestCount: () => requests.length, nodes, layers, views, finish, select, page, handlers, fits: () => fits, scrolls: () => scrolls };
}

test('seleccionar un dispositivo centra el mapa, abre la ficha y resalta la fila', async () => {
    const ui = setup(1);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    assert.equal(ui.nodes['button-1'].disabled, false);
    ui.select(1);
    assert.equal(ui.views.at(-1).zoom, 16);
    assert.deepEqual(Array.from(ui.views.at(-1).position), [-34.9, -57.9]);
    assert.equal(ui.layers[0].opened, true);
    assert.equal(ui.nodes['map-device-1'].classList.contains('table-active'), true);
    assert.equal(ui.scrolls(), 1);
});

test('la carga posterior conserva el punto elegido y otro botón permite cambiarlo', async () => {
    const ui = setup();
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    ui.select(1);
    const fits = ui.fits();
    await ui.finish(1, { status: 'located', lat: -32.9, lon: -60.6 });
    assert.equal(ui.fits(), fits);
    ui.select(2);
    assert.deepEqual(Array.from(ui.views.at(-1).position), [-32.9, -60.6]);
    assert.equal(ui.nodes['map-device-1'].classList.contains('table-active'), false);
    assert.equal(ui.nodes['map-device-2'].classList.contains('table-active'), true);
});

test('una dirección ambigua no habilita ni centra un marcador', async () => {
    const ui = setup(1);
    await ui.finish(0, { status: 'ambiguous' });
    assert.equal(ui.nodes['button-1'].disabled, true);
    assert.equal(ui.nodes['button-1'].title, 'Dirección ambigua');
    ui.select(1, true);
    assert.equal(ui.views.length, 1);
    assert.equal(ui.layers.length, 0);
});


test('el filtro de estado sincroniza tabla y marcadores', async () => {
    const ui = setup(2, '', [{ op: 'eq', value: 'located' }]);
    assert.equal(ui.nodes['map-device-1'].hidden, true);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    await ui.finish(1, { status: 'ambiguous' });
    assert.equal(ui.nodes['map-device-1'].hidden, false);
    assert.equal(ui.nodes['map-device-2'].hidden, true);
    assert.equal(ui.layers.length, 1);
    assert.equal(ui.nodes['map-filter-empty'].hidden, true);
});

test('el estado permite excluir una coincidencia con ne', async () => {
    const ui = setup(1, '', [{ op: 'ne', value: 'located' }]);
    assert.equal(ui.nodes['map-device-1'].hidden, false);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    assert.equal(ui.nodes['map-device-1'].hidden, true);
    assert.equal(ui.layers.length, 0);
    assert.equal(ui.nodes['map-filter-empty'].hidden, false);
});

test('la ficha incluye contacto y el enlace directo selecciona el punto solicitado', async () => {
    const ui = setup(1, '1');
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    assert.equal(ui.layers[0].opened, true);
    assert.equal(ui.views.at(-1).zoom, 16);
    const content = ui.layers[0].popup.children.map(child => child.textContent);
    assert.equal(content.includes('Representante: Representante 1'), true);
    assert.equal(content.includes('Teléfono: 221 5550001'), true);
    assert.equal(content.includes('Ver detalle'), true);
});

test('pulsar una fila no navega implícitamente', async () => {
    const ui = setup(1);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    ui.select(1, true);
    assert.equal(ui.views.length, 1);
    assert.equal(ui.scrolls(), 0);
});


test('la tabla pagina de a 15 sin quitar marcadores de otras páginas', async () => {
    const ui = setup(16);
    assert.equal(ui.nodes['map-device-15'].hidden, false);
    assert.equal(ui.nodes['map-device-16'].hidden, true);
    assert.equal(ui.nodes['map-pagination'].hidden, false);
    for (let i = 0; i < 16; i += 1) await ui.finish(i, { status: 'located', lat: -34.9, lon: -57.9 });
    ui.page('Continuar');
    assert.equal(ui.nodes['map-device-1'].hidden, true);
    assert.equal(ui.nodes['map-device-16'].hidden, false);
    assert.equal(ui.nodes['map-filter-count'].textContent, 'Mostrando 16–16 de 16 dispositivos');
    assert.equal(ui.layers.length, 16);
    ui.page('Volver');
    assert.equal(ui.nodes['map-device-1'].hidden, false);
    assert.equal(ui.nodes['map-device-16'].hidden, true);
});

test('la paginación se ajusta cuando cambian los estados pendientes', async () => {
    const ui = setup(16, '', [{ op: 'eq', value: 'pending' }]);
    ui.page('Continuar');
    assert.equal(ui.nodes['map-device-16'].hidden, false);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    assert.equal(ui.nodes['map-device-1'].hidden, true);
    assert.equal(ui.nodes['map-device-2'].hidden, false);
    assert.equal(ui.nodes['map-pagination'].hidden, true);
    assert.equal(ui.nodes['map-filter-count'].textContent, 'Mostrando 1–15 de 15 dispositivos');
});

test('abrir un marcador de otra página muestra también su fila', async () => {
    const ui = setup(16);
    for (let i = 0; i < 16; i += 1) await ui.finish(i, { status: 'located', lat: -34.9, lon: -57.9 });
    ui.layers[15].openPopup();
    assert.equal(ui.nodes['map-device-16'].hidden, false);
    assert.equal(ui.nodes['map-device-16'].classList.contains('table-active'), true);
    assert.equal(ui.nodes['map-device-1'].hidden, true);
});


test('las ubicaciones guardadas se dibujan sin solicitudes y conservan sus fichas', () => {
    const ui = setup(2, '', [], [1, 2]);
    assert.equal(ui.requestCount(), 0);
    assert.equal(ui.layers.length, 2);
    assert.equal(ui.nodes['map-status'].textContent.includes('2 guardados'), true);
    ui.select(2);
    assert.equal(ui.layers[1].opened, true);
});

test('un fallo de Georef no impide mostrar las ubicaciones ya guardadas', async () => {
    const ui = setup(2, '', [], [2]);
    assert.equal(ui.layers.length, 1);
    assert.equal(ui.nodes['button-2'].disabled, false);
    await ui.finish(0, { status: 'unavailable' });
    assert.equal(ui.layers.length, 1);
    assert.equal(ui.requestCount(), 1);
    ui.select(2);
    assert.equal(ui.layers[0].opened, true);
});


test('todos los puntos ubicados permanecen visibles al seleccionar otro dispositivo', async () => {
    const ui = setup(2);
    await ui.finish(0, { status: 'located', lat: -34.9, lon: -57.9 });
    await ui.finish(1, { status: 'located', lat: -32.9, lon: -60.6 });
    ui.select(1);
    ui.select(2);
    assert.equal(ui.layers.length, 2);
    assert.equal(ui.layers[1].opened, true);
});
