const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function setupForm() {
    function input() {
        const handlers = {};
        return {
            value: "",
            addEventListener(name, callback) {
                handlers[name] = callback;
            },
            dispatch(name, event = {}) {
                handlers[name]?.(event);
            },
        };
    }
    const amount = input();
    const quantity = input();
    const document = {
        addEventListener(name, callback) {
            assert.equal(name, "DOMContentLoaded");
            callback();
        },
        querySelectorAll(selector) {
            return selector === "[data-monto-entero]" ? [amount] : [quantity];
        },
    };
    const source = fs.readFileSync(
        path.join(__dirname, "../../comedores/static/custom/js/convenio_pnud.js"),
        "utf8",
    );
    vm.runInNewContext(source, { document });
    return { amount, quantity };
}

test("pasting a decimal amount preserves it for server-side rejection", () => {
    const { amount } = setupForm();
    amount.value = "100,50";
    amount.dispatch("input", { inputType: "insertFromPaste" });
    amount.dispatch("blur");
    assert.equal(amount.value, "100,50");
});

test("valid whole-peso amounts retain thousands formatting on blur", () => {
    const { amount } = setupForm();
    amount.value = "100000000";
    amount.dispatch("input");
    amount.dispatch("blur");
    assert.equal(amount.value, "100.000.000");
});

test("quantity inputs continue rejecting non-numeric pasted content", () => {
    const { quantity } = setupForm();
    let prevented = false;
    quantity.dispatch("paste", {
        clipboardData: { getData: () => "100,50" },
        preventDefault() { prevented = true; },
    });
    assert.equal(prevented, true);
});