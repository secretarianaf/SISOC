const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function visor(textareas = [], selectores = []) {
    const handlers = {};
    let reloads = 0;
    class Element {
        constructor(archivo) { this.archivo = archivo; }
        closest() { return this.archivo; }
    }
    const document = {
        visibilityState: 'visible',
        addEventListener(name, callback) { handlers[name] = callback; },
        querySelectorAll(query) {
            if (query === 'textarea[name="observaciones"]') return textareas;
            return query === '.js-documento-estado' ? selectores : [];
        },
    };
    const window = {
        location: { reload() { reloads++; } },
        addEventListener(name, callback) { handlers[name] = callback; },
    };
    const source = fs.readFileSync(path.join(__dirname, '../../static/custom/js/rendicioncuentasmensual_detail.js'), 'utf8');
    vm.runInNewContext(source, { document, window, Element });
    return { handlers, document, Element, reloads: () => reloads };
}

test('volver al detalle después de abrir un archivo refresca una sola vez', () => {
    const view = visor();
    view.handlers.click({ target: new view.Element(true) });
    view.document.visibilityState = 'hidden';
    view.handlers.visibilitychange();
    assert.equal(view.reloads(), 0);
    view.document.visibilityState = 'visible';
    view.handlers.visibilitychange();
    view.handlers.focus();
    assert.equal(view.reloads(), 1);
});

test('recuperar el foco sin abrir documentos conserva el formulario', () => {
    const view = visor();
    view.handlers.click({ target: new view.Element(false) });
    view.handlers.focus();
    assert.equal(view.reloads(), 0);
});

test('abrir un archivo en segundo plano no refresca en el próximo foco', () => {
    const view = visor();
    view.handlers.click({ target: new view.Element(true) });
    view.handlers.focus();
    assert.equal(view.reloads(), 0);
});

test('volver del visor con una observación sin guardar posterga el refresco', () => {
    const textarea = { value: 'Falta la firma' };
    const view = visor([textarea]);
    view.handlers.click({ target: new view.Element(true) });
    view.handlers.blur();
    view.handlers.focus();
    assert.equal(view.reloads(), 0);
    textarea.value = '';
    view.handlers.blur();
    view.handlers.focus();
    assert.equal(view.reloads(), 1);
});

test('volver del visor con un estado elegido sin guardar posterga el refresco', () => {
    const selector = { value: 'validado' };
    const view = visor([], [selector]);
    view.handlers.click({ target: new view.Element(true) });
    view.handlers.blur();
    view.handlers.focus();
    assert.equal(view.reloads(), 0);
    selector.value = '';
    view.handlers.blur();
    view.handlers.focus();
    assert.equal(view.reloads(), 1);
});

test('la revisión muestra la observación anterior sin abrir el editor', () => {
    const view = visor();
    const visibility = new Map();
    const editor = { classList: { toggle(name, hidden) { visibility.set('editor:' + name, hidden); } } };
    const input = { value: '', parentElement: editor };
    const row = { classList: { toggle(name, hidden) { visibility.set('row:' + name, hidden); } } };
    const selector = { value: '', dataset: { documentoId: '1' }, addEventListener() {} };
    const elements = {
        'observaciones-1': input,
        'observaciones-row-1': row,
        'observaciones-display-1': {},
    };
    view.document.getElementById = (id) => elements[id] || null;
    view.document.querySelectorAll = (query) => query === '.js-documento-estado' ? [selector] : [];
    view.handlers.DOMContentLoaded();
    assert.equal(visibility.get('row:d-none'), false);
    assert.equal(visibility.get('editor:d-none'), true);
});

test('categoría filtra actividades y conserva la selección al editar', () => {
    const callbacks = {};
    const category = { value: 'Salud', addEventListener(event, callback) { callbacks[event] = callback; } };
    const activity = {
        value: '2', options: [],
        replaceChildren(...options) { this.options = options; this.value = ''; },
        add(option) { this.options.push(option); if (option.selected) this.value = option.value; },
    };
    const options = { textContent: JSON.stringify([
        { id: 1, categoria: 'Arte', actividad: 'Dibujo' },
        { id: 2, categoria: 'Salud', actividad: 'Yoga' },
    ]) };
    const source = fs.readFileSync(path.join(__dirname, '../../../comedores/templates/comedor/actividad_espacio_pwa_form.html'), 'utf8');
    const script = source.match(/<script nonce="[^"]*">([\s\S]*?)<\/script>/)[1];
    vm.runInNewContext(script, {
        document: { getElementById(id) { return { id_categoria: category, id_catalogo_actividad: activity, 'activity-options': options }[id] || null; } },
        Option: function (text, value, defaultSelected, selected) { Object.assign(this, { text, value, selected }); },
    });
    assert.deepEqual(activity.options.map((option) => option.text), ['Seleccionar', 'Yoga']);
    assert.equal(activity.value, '2');
    category.value = 'Arte';
    callbacks.change();
    assert.deepEqual(activity.options.map((option) => option.text), ['Seleccionar', 'Dibujo']);
    assert.equal(activity.value, '');
    category.value = '';
    callbacks.change();
    assert.equal(activity.disabled, true);
});
