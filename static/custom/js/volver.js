/**
 * "Volver" unificado del sistema (issue #2460).
 *
 * El requisito no es solo estetico: al volver tienen que seguir aplicados los
 * filtros de la pantalla anterior. Por eso no alcanza con un href fijo al
 * listado (perderia la querystring) ni con history.back() a secas.
 *
 * El destino se resuelve combinando dos fuentes, y el orden importa:
 *
 * 1. `volver_url`, el destino **jerarquico** que declara la vista (el detalle
 *    de una nomina vuelve al CDI, no a la pantalla anterior). Si en la pila hay
 *    una visita a ese mismo path, se usa la de la pila, que trae la
 *    querystring: asi el destino es el correcto y ademas conserva los filtros.
 * 2. La pila de navegacion, cuando la vista no declara destino.
 * 3. El referrer, si es del mismo origen.
 * 4. La raiz.
 *
 * Nunca se llama a `history.back()`: con un referrer externo o vacio (link de
 * mail, pestaña nueva) sacaba al usuario de SISOC.
 *
 * Las pantallas **transitorias** (altas, ediciones, confirmaciones de borrado)
 * no se apilan. Si se apilaran, un POST-redirect-GET dejaria el formulario como
 * "pantalla anterior" y "Volver" llevaria al alta vacia o al confirm_delete de
 * un objeto ya borrado. Quien marca la pantalla es el servidor, via
 * `data-volver-transitoria` en el <script> (ver core.context_processors).
 */
(function (window, document) {
    "use strict";

    var CLAVE_PILA = "sisocNavStack";
    var MAX_ENTRADAS = 25;

    // Se lee en tiempo de parseo, antes de que corra registrarVisita().
    var script = document.currentScript;
    var ES_TRANSITORIA = !!(
        script && script.getAttribute("data-volver-transitoria") === "1"
    );

    function urlActual() {
        return window.location.pathname + window.location.search;
    }

    function soloPath(url) {
        var corte = url.indexOf("?");
        return corte === -1 ? url : url.slice(0, corte);
    }

    function leerPila() {
        try {
            var crudo = window.sessionStorage.getItem(CLAVE_PILA);
            var pila = crudo ? JSON.parse(crudo) : [];
            return Array.isArray(pila) ? pila : [];
        } catch (error) {
            return [];
        }
    }

    function guardarPila(pila) {
        try {
            window.sessionStorage.setItem(CLAVE_PILA, JSON.stringify(pila));
        } catch (error) {
            // Navegacion privada o storage lleno: el boton sigue andando por fallback.
        }
    }

    /**
     * Registra la pantalla actual.
     *
     * - Las transitorias no se apilan: son un paso del flujo, no un destino.
     * - Si repite la ultima entrada (F5, o POST que re-renderiza la misma URL)
     *   no se apila de nuevo.
     * - Si coincide con la anteultima, se interpreta como "el usuario volvio" y
     *   se desapila, para que la pila no crezca en zigzag.
     */
    function registrarVisita() {
        var pila = leerPila();
        if (ES_TRANSITORIA) {
            return pila;
        }

        var actual = urlActual();
        if (pila.length && pila[pila.length - 1] === actual) {
            return pila;
        }
        if (pila.length > 1 && pila[pila.length - 2] === actual) {
            pila.pop();
            guardarPila(pila);
            return pila;
        }

        pila.push(actual);
        if (pila.length > MAX_ENTRADAS) {
            pila = pila.slice(pila.length - MAX_ENTRADAS);
        }
        guardarPila(pila);
        return pila;
    }

    /** URL anterior distinta de la actual, o null. */
    function destinoPrevio() {
        var pila = leerPila();
        var actual = urlActual();
        for (var i = pila.length - 1; i >= 0; i--) {
            if (pila[i] !== actual) {
                return pila[i];
            }
        }
        return null;
    }

    /**
     * El destino jerarquico que declaro la vista, enriquecido con la
     * querystring si esa misma pantalla esta en la pila (se la visito filtrada).
     */
    function destinoDeclarado(fallback) {
        if (!fallback) return null;

        var pila = leerPila();
        var path = soloPath(fallback);
        for (var i = pila.length - 1; i >= 0; i--) {
            if (soloPath(pila[i]) === path) {
                return pila[i];
            }
        }
        return fallback;
    }

    /** El referrer solo sirve si es del mismo origen. */
    function referrerInterno() {
        if (!document.referrer) return null;
        try {
            var referrer = new URL(document.referrer);
            if (referrer.origin !== window.location.origin) return null;
            var destino = referrer.pathname + referrer.search;
            return destino === urlActual() ? null : destino;
        } catch (error) {
            return null;
        }
    }

    function resolverDestino(boton) {
        return (
            destinoDeclarado(boton.dataset.volverFallback) ||
            destinoPrevio() ||
            referrerInterno() ||
            "/"
        );
    }

    function conectar(boton) {
        boton.setAttribute("href", resolverDestino(boton));
    }

    registrarVisita();

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-sisoc-volver]").forEach(conectar);
    });

    // Expuesto para los tests y para pantallas que reconstruyen el boton.
    window.SisocVolver = {
        registrarVisita: registrarVisita,
        destinoPrevio: destinoPrevio,
        destinoDeclarado: destinoDeclarado,
        resolverDestino: resolverDestino,
        conectar: conectar,
        esTransitoria: ES_TRANSITORIA,
    };
})(window, document);
