/**
 * CDI - CASILLA "NO POSEE CUIL"
 *
 * Marcar la casilla vacía el CUIT y lo deja de exigir; cargar un CUIT (a mano o
 * desde RENAPER) la desmarca. El servidor valida lo mismo: esto solo ordena la
 * pantalla.
 */

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-sin-cuil-de]").forEach(initializeSinCuil);
});

function initializeSinCuil(casilla) {
    const cuit = document.getElementById(casilla.dataset.sinCuilDe);
    if (!cuit) return;
    // Si se renderizó marcada, el servidor ya le sacó el required al CUIT.
    const requerido = cuit.required || casilla.checked;

    function aplicar() {
        if (casilla.checked) cuit.value = "";
        cuit.readOnly = casilla.checked || cuit.dataset.renaper === "1";
        cuit.required = requerido && !casilla.checked;
    }

    casilla.addEventListener("change", aplicar);
    cuit.addEventListener("change", function () {
        if (cuit.value) casilla.checked = false;
        aplicar();
    });
    aplicar();
}
