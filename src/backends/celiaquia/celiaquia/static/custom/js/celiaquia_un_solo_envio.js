// Evita el doble envío de los formularios clásicos de Celiaquía (POST con
// recarga de página) marcados con `data-un-solo-envio="Texto…"` (issue #2892).
//
// El primer submit deshabilita el botón y le pone un spinner con ese texto;
// los siguientes se ignoran hasta que la página se recargue. Un doble clic en
// "Generar expediente de pago", por ejemplo, creaba dos expedientes.
(function () {
    const SPINNER = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>';

    function marcarEnviando(boton, texto) {
        if (!boton) return;
        boton.dataset.htmlOriginal = boton.innerHTML;
        boton.disabled = true;
        boton.innerHTML = `${SPINNER}${texto}`;
    }

    function restaurar(boton) {
        if (!boton) return;
        boton.disabled = false;
        if (boton.dataset.htmlOriginal !== undefined) {
            boton.innerHTML = boton.dataset.htmlOriginal;
            delete boton.dataset.htmlOriginal;
        }
    }

    document.addEventListener('submit', (e) => {
        const form = e.target;
        if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-un-solo-envio')) return;
        // Otro script canceló el envío (p. ej. una validación): no se bloquea nada.
        if (e.defaultPrevented) return;

        if (form.dataset.enviando === 'true') {
            e.preventDefault();
            return;
        }
        form.dataset.enviando = 'true';

        const boton = e.submitter || form.querySelector('[type="submit"], button:not([type])');
        const texto = form.dataset.unSoloEnvio || 'Enviando…';
        // Se difiere para que el navegador arme los datos del form antes de
        // deshabilitar el botón (un botón deshabilitado no se envía).
        setTimeout(() => marcarEnviando(boton, texto), 0);
    });

    // Al volver con "Atrás" el navegador puede restaurar la página tal como
    // quedó, con el botón bloqueado: se lo vuelve a habilitar.
    window.addEventListener('pageshow', (e) => {
        if (!e.persisted) return;
        document.querySelectorAll('form[data-un-solo-envio][data-enviando="true"]').forEach((form) => {
            form.dataset.enviando = 'false';
            form.querySelectorAll('[data-html-original]').forEach(restaurar);
        });
    });
})();
