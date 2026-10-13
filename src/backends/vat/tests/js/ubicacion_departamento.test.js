// Ejecutar: node --test src/backends/vat/tests/js/ubicacion_departamento.test.js
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const template = readFileSync(
    resolve(__dirname, '../../VAT/templates/vat/centros/centro_detail.html'), 'utf8'
);
const customJS = template.indexOf('{% block customJS %}');
const cascade = template.slice(
    template.indexOf('function setupUbicacionDepartamentoCascade('),
    template.indexOf('function setupUbicacionModalSelect2(')
);
const init = /^\s*setupUbicacionDepartamentoCascade\('formUbicacion', 'modalUbicacion'\);/gm;

function escenario({ jquery = true, departamento = '', localidad = '' } = {}) {
    const requests = [];
    const nativeHandlers = {};
    const jqueryHandlers = {};
    const modalHandlers = {};
    const form = {
        dataset: {},
        querySelector: selector => fields[selector],
        addEventListener: (event, handler) => { nativeHandlers[event] = handler; },
    };
    const modal = { addEventListener: (event, handler) => { modalHandlers[event] = handler; } };
    let fields;
    function reemplazarCampos(depto = '', loc = '') {
        const localidadSelect = {
            value: loc,
            disabled: false,
            options: [],
            set innerHTML(html) {
                this.options = [{ value: '', textContent: html }];
                this.value = '';
            },
            appendChild(option) {
                this.options.push(option);
                if (option.selected) this.value = String(option.value);
            },
        };
        fields = {
            '#id_departamento_ubicacion': {
                id: 'id_departamento_ubicacion', value: depto,
                options: [{ value: '' }, { value: '12' }, { value: '13' }],
            },
            '#id_localidad_ubicacion': localidadSelect,
        };
    }
    reemplazarCampos(departamento, localidad);
    const context = {
        window: {}, console,
        document: {
            getElementById: id => id === 'formUbicacion' ? form : modal,
            createElement: () => ({}),
        },
        fetch: async url => {
            requests.push(url);
            return { ok: true, json: async () => [{ id: 21, nombre: 'Localidad del departamento' }] };
        },
    };
    // El content se ejecuta antes de mainscripts: jQuery todavía no existe.
    const functionOnly = cascade.slice(0, cascade.lastIndexOf('}')) + '}';
    runInNewContext(functionOnly, context);
    for (const call of template.slice(0, customJS).matchAll(init)) {
        runInNewContext(call[0], context);
    }
    if (jquery) {
        context.window.jQuery = () => ({
            on(events, selector, handler) {
                events.split(' ').forEach(event => { jqueryHandlers[event] = handler; });
            },
            trigger() {},
        });
    }
    for (const call of template.slice(customJS).matchAll(init)) {
        runInNewContext(call[0], context);
    }
    return {
        requests, reemplazarCampos,
        localidad: () => fields['#id_localidad_ubicacion'],
        abrir: () => modalHandlers['shown.bs.modal'](),
        cambiar(event = 'change') {
            fields['#id_departamento_ubicacion'].value = '12';
            if (jquery) jqueryHandlers[event]?.();
            else nativeHandlers.change?.({ target: fields['#id_departamento_ubicacion'] });
        },
    };
}

const completarCarga = () => new Promise(resolve => setImmediate(resolve));

for (const evento of ['change', 'select2:select']) {
    test(`elegir departamento con Select2 carga localidades (${evento})`, async () => {
        const browser = escenario();
        browser.abrir();
        assert.equal(browser.localidad().disabled, true);
        // Agregar/editar reemplaza los campos, pero conserva el form envolvente.
        browser.reemplazarCampos();
        browser.cambiar(evento);
        await completarCarga();
        assert.equal(browser.requests.length, 1);
        assert.match(browser.requests[0], /\?municipio_id=12$/);
        assert.equal(browser.localidad().disabled, false);
        assert.equal(browser.localidad().options[1].textContent, 'Localidad del departamento');
    });
}

test('sin jQuery el cambio nativo sigue cargando localidades', async () => {
    const browser = escenario({ jquery: false });
    browser.cambiar();
    await completarCarga();
    assert.equal(browser.requests.length, 1);
    assert.equal(browser.localidad().disabled, false);
});

test('abrir edición conserva la localidad guardada del departamento', async () => {
    const browser = escenario({ departamento: '12', localidad: '21' });
    browser.abrir();
    await completarCarga();
    assert.equal(browser.requests.length, 1);
    assert.equal(browser.localidad().value, '21');
    assert.equal(browser.localidad().disabled, false);
});
