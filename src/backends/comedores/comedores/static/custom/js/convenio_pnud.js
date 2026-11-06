document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-monto-entero]").forEach(function (input) {
        input.addEventListener("input", function () {
            // Montos sin centavos: solo dígitos y los puntos de miles.
            const limpio = input.value.replace(/[^0-9.]/g, "");
            if (limpio !== input.value) {
                input.value = limpio;
            }
        });
        input.addEventListener("blur", function () {
            const valor = input.value.trim();
            if (/^-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)$/.test(valor)) {
                input.value = valor.replace(/\./g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
            }
        });
    });

    // Campos de cantidades: solo números enteros (sin "e", signos ni decimales).
    document.querySelectorAll("[data-solo-numeros]").forEach(function (input) {
        input.addEventListener("keydown", function (event) {
            if (["e", "E", "+", "-", ".", ","].includes(event.key)) {
                event.preventDefault();
            }
        });
        input.addEventListener("paste", function (event) {
            const texto = (event.clipboardData || window.clipboardData).getData("text");
            if (!/^[0-9]+$/.test(texto.trim())) {
                event.preventDefault();
            }
        });
    });
});
