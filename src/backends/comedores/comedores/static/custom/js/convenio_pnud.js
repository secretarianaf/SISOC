document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-monto-entero]").forEach(function (input) {
        input.addEventListener("blur", function () {
            const valor = input.value.trim();
            if (/^-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)$/.test(valor)) {
                input.value = valor.replace(/\./g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
            }
        });
    });
});
