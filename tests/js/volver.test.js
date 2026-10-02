/**
 * "Volver" unificado: resolucion del destino (issue #2460, review del PR #2567).
 *
 * Cubre los tres flujos que el review marco como rotos (alta, borrado y edicion
 * con redirect al listado), mas la pila, el zigzag y la entrada directa.
 *
 * Correr con:  node --test tests/js/volver.test.js
 */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const CODIGO = readFileSync(
  resolve(__dirname, '../../static/custom/js/volver.js'),
  'utf8',
);

const ORIGEN = 'https://sisoc.test';

/**
 * Simula una sesion del navegador: el sessionStorage sobrevive entre pantallas,
 * como en la realidad.
 */
function nuevaSesion() {
  const almacen = new Map();
  const sessionStorage = {
    getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
    setItem: (k, v) => almacen.set(k, String(v)),
  };

  /**
   * Carga una pantalla y devuelve el href que quedaria en el boton "Volver".
   *
   * @param {string} url          path + querystring de la pantalla
   * @param {object} opciones     {transitoria, volverUrl, referrer}
   */
  function visitar(url, opciones = {}) {
    const { transitoria = false, volverUrl = '', referrer = '' } = opciones;

    const boton = { dataset: { volverFallback: volverUrl }, atributos: {} };
    boton.setAttribute = (nombre, valor) => {
      boton.atributos[nombre] = valor;
    };

    const [pathname, busqueda] = url.split('?');
    const contexto = {
      window: {
        location: { pathname, search: busqueda ? `?${busqueda}` : '', origin: ORIGEN },
        sessionStorage,
        history: { length: 5, back: () => { throw new Error('no debe usarse history.back()'); } },
      },
      document: {
        referrer,
        currentScript: {
          getAttribute: (n) =>
            n === 'data-volver-transitoria' ? (transitoria ? '1' : '0') : null,
        },
        addEventListener: () => {},
        querySelectorAll: () => [],
      },
      URL,
    };
    contexto.window.window = contexto.window;
    contexto.window.document = contexto.document;

    runInNewContext(CODIGO, contexto);
    contexto.window.SisocVolver.conectar(boton);
    return boton.atributos.href;
  }

  return { visitar, pila: () => JSON.parse(sessionStorage.getItem('sisocNavStack') || '[]') };
}

test('vuelve al listado conservando los filtros', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/comedores/?provincia=chaco&estado=activo');
  const destino = sesion.visitar('/comedores/12/');

  assert.equal(destino, '/comedores/?provincia=chaco&estado=activo');
});

test('alta: el detalle nuevo no vuelve al formulario vacio', () => {
  // /comedores/ -> /comedores/crear (transitoria) -> POST -> /comedores/12/
  const sesion = nuevaSesion();
  sesion.visitar('/comedores/?provincia=chaco');
  sesion.visitar('/comedores/crear', { transitoria: true });
  const destino = sesion.visitar('/comedores/12/');

  assert.equal(destino, '/comedores/?provincia=chaco');
  assert.deepEqual(sesion.pila(), ['/comedores/?provincia=chaco', '/comedores/12/']);
});

test('borrado: el listado no vuelve al confirm_delete de un objeto que ya no existe', () => {
  // /ofertas/ -> /ofertas/7/ -> /ofertas/7/eliminar (transitoria) -> POST -> /ofertas/
  const sesion = nuevaSesion();
  sesion.visitar('/ofertas/');
  sesion.visitar('/ofertas/7/');
  sesion.visitar('/ofertas/7/eliminar', { transitoria: true });
  const destino = sesion.visitar('/ofertas/');

  assert.ok(!destino.includes('eliminar'), `no debe volver al confirm_delete: ${destino}`);
  assert.deepEqual(sesion.pila(), ['/ofertas/']);
});

test('edicion con success_url al listado: no vuelve al formulario de edicion', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/organizaciones/');
  sesion.visitar('/organizaciones/3/');
  sesion.visitar('/organizaciones/3/editar', { transitoria: true });
  const destino = sesion.visitar('/organizaciones/');

  assert.ok(!destino.includes('editar'), `no debe volver al form: ${destino}`);
});

test('el destino jerarquico de la vista gana sobre la pantalla anterior', () => {
  // Se llega a la nomina desde una busqueda global, no desde el CDI.
  const sesion = nuevaSesion();
  sesion.visitar('/buscador/?q=nomina');
  const destino = sesion.visitar('/cdi/5/nomina/9/', { volverUrl: '/cdi/5/' });

  assert.equal(destino, '/cdi/5/');
});

test('el destino jerarquico recupera la querystring si esa pantalla se visito filtrada', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/cdi/?provincia=salta');
  sesion.visitar('/cdi/5/');
  const destino = sesion.visitar('/cdi/5/nomina/9/', { volverUrl: '/cdi/' });

  assert.equal(destino, '/cdi/?provincia=salta');
});

test('entrada directa sin historial ni referrer cae a la raiz, nunca a history.back()', () => {
  const sesion = nuevaSesion();
  const destino = sesion.visitar('/comedores/12/');

  assert.equal(destino, '/');
});

test('entrada directa usa el destino declarado por la vista', () => {
  const sesion = nuevaSesion();
  const destino = sesion.visitar('/cdi/5/nomina/9/', { volverUrl: '/cdi/5/' });

  assert.equal(destino, '/cdi/5/');
});

test('un referrer externo no saca al usuario de SISOC', () => {
  const sesion = nuevaSesion();
  const destino = sesion.visitar('/comedores/12/', {
    referrer: 'https://mail.google.com/algo',
  });

  assert.equal(destino, '/');
});

test('recargar no duplica la entrada en la pila', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/comedores/');
  sesion.visitar('/comedores/');
  sesion.visitar('/comedores/');

  assert.deepEqual(sesion.pila(), ['/comedores/']);
});

test('el zigzag desapila en vez de crecer', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/comedores/');
  sesion.visitar('/comedores/12/');
  sesion.visitar('/comedores/');

  assert.deepEqual(sesion.pila(), ['/comedores/']);
});

test('una pantalla transitoria nunca se apila', () => {
  const sesion = nuevaSesion();
  sesion.visitar('/comedores/');
  sesion.visitar('/comedores/crear', { transitoria: true });

  assert.deepEqual(sesion.pila(), ['/comedores/']);
});
