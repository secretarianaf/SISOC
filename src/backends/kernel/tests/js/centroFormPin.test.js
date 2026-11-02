const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../static/custom/js/centro_form.js'), 'utf8');
function setup(type = '') {
    const nodes = {};
    for (const id of ['id_tipo', 'id_provincia', 'id_municipio', 'id_localidad']) {
        nodes[id] = { value: '', handlers: {}, addEventListener(name, cb) { this.handlers[name] = cb; } };
    }
    nodes.id_tipo.value = type;
    const wrappers = ['tipo', 'nombre', 'calle', 'numero', 'latitud', 'longitud', 'faro_asociado'].map(name => ({ id: `div_id_${name}`, style: {} }));
    const editor = { hidden: false };
    const events = [];
    runInNewContext(source, {
        document: {
            addEventListener: (_, cb) => cb(),
            getElementById: id => nodes[id],
            querySelectorAll: () => wrappers,
            querySelector: () => editor,
        },
        window: { dispatchEvent: event => events.push(event.type) },
        Event: function(type) { this.type = type; },
    });
    return { nodes, wrappers, editor, events };
}
test('sin tipo no muestra un mapa aislado antes del domicilio', () => {
    const { wrappers, editor } = setup();
    assert.equal(editor.hidden, true);
    assert.equal(wrappers.find(item => item.id === 'div_id_latitud').style.display, 'none');
});
test('Faro y Adherido muestran coordenadas junto con los datos y el mapa', () => {
    for (const type of ['faro', 'adherido']) {
        const { wrappers, editor, events } = setup(type);
        for (const name of ['calle', 'numero', 'latitud', 'longitud']) {
            assert.equal(wrappers.find(item => item.id === `div_id_${name}`).style.display, 'block');
        }
        assert.equal(editor.hidden, false);
        assert.deepEqual(events, ['resize']);
    }
});
test('cambiar tipo mantiene visibles coordenadas y acompaña el resto del formulario', () => {
    const { nodes, wrappers, editor } = setup();
    nodes.id_tipo.value = 'faro';
    nodes.id_tipo.handlers.change();
    assert.equal(editor.hidden, false);
    assert.equal(wrappers.find(item => item.id === 'div_id_latitud').style.display, 'block');
    nodes.id_tipo.value = '';
    nodes.id_tipo.handlers.change();
    assert.equal(editor.hidden, true);
});
