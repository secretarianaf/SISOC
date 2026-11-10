const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");

const source = readFileSync(resolve(__dirname, "../../static/custom/js/encuestaPreguntasBuilder.js"), "utf8");

class Element {
    constructor() {
        this.children = [];
        this.handlers = {};
        this.value = "";
        this.checked = false;
        this.textContent = "";
        this.classes = new Set();
        this.classList = {
            add: name => this.classes.add(name),
            remove: (...names) => names.forEach(name => this.classes.delete(name)),
            contains: name => this.classes.has(name),
            toggle: (name, active) => active ? this.classes.add(name) : this.classes.delete(name),
        };
    }
    set innerHTML(value) { this.children = []; }
    addEventListener(name, handler) { this.handlers[name] = handler; }
    fire(name, event = {}) { this.handlers[name](event); }
    appendChild(child) { this.insertBefore(child, null); }
    insertBefore(child, next) {
        if (this.onInsert) this.onInsert(child, next);
        if (child.parent) child.remove();
        const index = next ? this.children.indexOf(next) : this.children.length;
        this.children.splice(index, 0, child);
        child.parent = this;
    }
    remove() {
        this.parent.children.splice(this.parent.children.indexOf(this), 1);
        this.parent = null;
    }
    get nextSibling() {
        return this.parent.children[this.parent.children.indexOf(this) + 1] || null;
    }
    getBoundingClientRect() { return { left: 20, top: 30 }; }
    contains(other) { return other === this || this.children.includes(other); }
    focus(options) { this.focused = true; this.focusOptions = options; }
    animate(keyframes, options) { this.animation = { keyframes, options }; }
}

function editor(initial) {
    const elements = Object.fromEntries([
        "preguntas-container", "pregunta-row-template", "agregar-pregunta", "preguntas_json",
        "preguntas-vacio-msg", "preguntas-cantidad", "encuesta-form", "preguntas-iniciales",
        "quitar-pregunta-modal", "quitar-pregunta-advertencia",
        "confirmar-quitar-pregunta", "cancelar-quitar-pregunta",
    ].map(id => [id, new Element()]));
    elements["preguntas-iniciales"].textContent = JSON.stringify(initial);
    elements["pregunta-row-template"].content = {
        cloneNode() {
            const row = new Element();
            const fields = {};
            row.querySelector = selector => {
                if (!fields[selector]) fields[selector] = new Element();
                return fields[selector];
            };
            row.querySelector(".pregunta-tipo").value = "texto_corto";
            row.querySelector(".pregunta-condicion-valor-select").classList.add("d-none");
            return { querySelector: () => row };
        },
    };
    const modal = {
        visible: false,
        show() { this.visible = true; elements["quitar-pregunta-modal"].fire("shown.bs.modal"); },
        hide() { this.visible = false; elements["quitar-pregunta-modal"].fire("hidden.bs.modal"); },
    };
    const timers = new Map();
    let timerId = 0;
    const doc = new Element();
    const viewport = {
        scrollX: 0, scrollY: 600,
        innerHeight: 900, innerWidth: 1200,
        setInterval(callback) { timers.set(++timerId, callback); return timerId; },
        clearInterval(id) { timers.delete(id); },
        scrollBy(position) { this.scrollY += position.top; },
        matchMedia: () => ({ matches: false }),
        scrollTo(position) { this.scrollX = position.left; this.scrollY = position.top; },
    };
    const notifications = [];
    const notify = type => (message, title, options) => notifications.push({ type, message, options });
    runInNewContext(source, {
        toastr: { success: notify("success"), warning: notify("warning") },
        window: viewport,
        bootstrap: { Modal: { getOrCreateInstance: () => modal } },
        requestAnimationFrame: callback => callback(),
        document: {
            addEventListener: (name, handler) => doc.addEventListener(name, handler),
            getElementById: id => elements[id],
            createElement: () => new Element(),
            querySelector: () => ({ getAttribute: name => name === "data-tipos-con-opciones"
                ? "opcion_unica,opcion_multiple" : "opcion_unica,opcion_multiple,si_no,escala" }),
        },
    });
    return {
        elements, modal, viewport, doc, timers, notifications,
        tick() { Array.from(timers.values()).forEach(callback => callback()); },
        rows: () => elements["preguntas-container"].children,
        drag(row, target) {
            const event = {
                clientX: 25, clientY: 40,
                dataTransfer: {
                    setData() {},
                    setDragImage(image, x, y) { this.image = image; this.offset = [x, y]; },
                },
                preventDefault() {},
            };
            row._preguntaRefs.arrastrar.fire("dragstart", event);
            target.fire("dragover", event);
            target.fire("drop", event);
            row._preguntaRefs.arrastrar.fire("dragend");
            return event;
        },
        saved() {
            elements["encuesta-form"].fire("submit");
            return JSON.parse(elements.preguntas_json.value);
        },
    };
}

const initial = [
    { orden: 1, texto: "Actividad", tipo: "opcion_unica", obligatoria: true,
        opciones: [{ texto: "Apoyo escolar", puntaje: 5 }, { texto: "Otra", puntaje: 2 }], pondera: true },
    { orden: 2, texto: "Internet", tipo: "si_no", obligatoria: true, pondera: true, puntaje_si: 3, puntaje_no: 1 },
    { orden: 3, texto: "Comentarios", tipo: "texto_largo", obligatoria: false },
];

test("las flechas en el ícono conservan opciones, puntajes y obligatoriedad", () => {
    const ui = editor(initial);
    const before = ui.saved();
    ui.rows()[1]._preguntaRefs.arrastrar.fire("keydown", { key: "ArrowUp", preventDefault() {} });
    assert.deepEqual(ui.saved(), [
        { ...before[1], orden: 1 }, { ...before[0], orden: 2 }, before[2],
    ]);
    ui.rows()[0]._preguntaRefs.arrastrar.fire("keydown", { key: "ArrowDown", preventDefault() {} });
    assert.deepEqual(ui.saved(), before);
    assert.equal(ui.rows()[1]._preguntaRefs.arrastrar.focused, true);
});

test("agregar y arrastrar al medio conserva las dependencias existentes", () => {
    const ui = editor([
        initial[2], { ...initial[1], orden: 2 },
        { ...initial[2], orden: 3, condicion: { orden: 2, operador: "igual", valor: "si" } },
    ]);
    ui.elements["agregar-pregunta"].fire("click");
    ui.rows()[3]._preguntaRefs.texto.value = "Nueva pregunta";
    ui.drag(ui.rows()[3], ui.rows()[1]);
    assert.equal(ui.saved()[3].condicion.orden, 3);
    assert.equal(ui.saved()[3].condicion.valor, "si");
    assert.deepEqual(ui.saved().map(q => q.orden), [1, 2, 3, 4]);
});

test("arrastrar mueve la fila y conserva la pregunta referenciada", () => {
    const ui = editor([
        initial[0], initial[1],
        { ...initial[2], condicion: { orden: 2, operador: "distinto", valor: "no" } },
    ]);
    const row = ui.rows()[1];
    const event = ui.drag(row, ui.rows()[0]);
    assert.equal(event.dataTransfer.image, row);
    assert.deepEqual(event.dataTransfer.offset, [5, 10]);
    assert.equal(ui.saved()[0].texto, "Internet");
    assert.deepEqual(ui.saved()[2].condicion, { orden: 1, operador: "distinto", valor: "no" });
    assert.equal(row.classList.contains("pregunta-arrastrando"), false);
});

test("rechaza mover una pregunta condicional antes de su referencia sin perder datos", () => {
    const ui = editor([
        initial[1], { ...initial[2], condicion: { orden: 1, operador: "igual", valor: "si" } },
    ]);
    const before = ui.saved();
    ui.rows()[1]._preguntaRefs.arrastrar.fire("keydown", { key: "ArrowUp", preventDefault() {} });
    assert.deepEqual(ui.saved(), before);
    assert.match(ui.notifications[0].message, /No se puede mover/);
    assert.equal(ui.notifications[0].type, "warning");
    ui.rows()[0]._preguntaRefs.arrastrar.fire("keydown", { key: "ArrowDown", preventDefault() {} });
    assert.deepEqual(ui.saved(), before);
});

test("cambiar la condición y borrar otra pregunta mantiene la referencia elegida", () => {
    const ui = editor(initial);
    const refs = ui.rows()[2]._preguntaRefs;
    refs.condicionRef.value = "2";
    refs.condicionRef.fire("change");
    refs.condicionOperador.value = "igual";
    refs.condicionValorSelect.value = "no";
    ui.rows()[0]._preguntaRefs.quitarBtn.fire("click");
    ui.elements["confirmar-quitar-pregunta"].fire("click");
    assert.deepEqual(ui.saved()[1].condicion, { orden: 1, operador: "igual", valor: "no" });
});

test("guardar y volver a hidratar mantiene el orden elegido", () => {
    const ui = editor(initial);
    ui.drag(ui.rows()[2], ui.rows()[1]);
    const saved = ui.saved();
    assert.deepEqual(editor(saved).saved(), saved);
});

test("el arrastre muestra la tarjeta completa y marca el destino hasta cancelar", () => {
    const ui = editor(initial);
    const row = ui.rows()[2];
    const target = ui.rows()[0];
    const before = ui.saved();
    let image;
    const event = {
        clientX: 25, clientY: 40,
        dataTransfer: { setData() {}, setDragImage(element) { image = element; } },
        preventDefault() {},
    };
    row._preguntaRefs.arrastrar.fire("dragstart", event);
    assert.equal(image, row);
    assert.equal(row.classList.contains("pregunta-arrastrando"), true);
    target.fire("dragover", event);
    assert.equal(target.classList.contains("pregunta-destino-antes"), true);
    // Salir de la tarjeta hacia el hueco que acaba de abrir no borra el destino.
    if (target.handlers.dragleave) target.fire("dragleave", { relatedTarget: null });
    assert.equal(target.classList.contains("pregunta-destino-antes"), true);
    let cambios = 0;
    const add = target.classList.add;
    target.classList.add = name => { cambios++; add(name); };
    target.fire("dragover", event);
    assert.equal(cambios, 0, "repetir dragover no reconstruye el espacio");
    row._preguntaRefs.arrastrar.fire("dragend");
    assert.equal(target.classList.contains("pregunta-destino-antes"), false);
    assert.equal(row.classList.contains("pregunta-arrastrando"), false);
    assert.deepEqual(ui.saved(), before);
});

test("cambiar de destino deja un solo skeleton y permite soltar en el hueco", () => {
    const ui = editor(initial);
    const row = ui.rows()[0];
    const anterior = ui.rows()[1];
    const siguiente = ui.rows()[2];
    const event = {
        clientX: 25, clientY: 40,
        dataTransfer: { setData() {}, setDragImage() {} }, preventDefault() {},
    };
    row._preguntaRefs.arrastrar.fire("dragstart", event);
    anterior.fire("dragover", event);
    siguiente.fire("dragover", event);
    assert.equal(anterior.classList.contains("pregunta-destino-despues"), false);
    assert.equal(siguiente.classList.contains("pregunta-destino-despues"), true);
    ui.doc.fire("drop", { target: ui.elements["preguntas-container"], preventDefault() {} });
    assert.equal(ui.saved()[2].texto, "Actividad");
    assert.equal(siguiente.classList.contains("pregunta-destino-despues"), false);
    row._preguntaRefs.arrastrar.fire("dragend");
});

test("arrastrar hacia abajo marca el borde inferior y limpia el indicador al soltar", () => {
    const ui = editor(initial);
    const row = ui.rows()[0];
    const target = ui.rows()[2];
    const event = {
        clientX: 25, clientY: 40,
        dataTransfer: { setData() {}, setDragImage() {} }, preventDefault() {},
    };
    row._preguntaRefs.arrastrar.fire("dragstart", event);
    target.fire("dragover", event);
    assert.equal(target.classList.contains("pregunta-destino-despues"), true);
    target.fire("drop", event);
    row._preguntaRefs.arrastrar.fire("dragend");
    assert.equal(ui.saved()[2].texto, "Actividad");
    assert.equal(target.classList.contains("pregunta-destino-despues"), false);
});

test("el template mantiene Quitar y solo agrega el ícono junto al número", () => {
    const template = readFileSync(resolve(__dirname, "../../templates/encuestas/encuesta_form.html"), "utf8");
    assert.match(template, /pregunta-identificador[\s\S]*pregunta-arrastrar[\s\S]*pregunta-numero/);
    assert.match(template, /btn-quitar-pregunta/);
    assert.doesNotMatch(template, /btn-(subir|bajar|insertar)-pregunta/);
});

test("abrir y cancelar el modal conserva todas las preguntas y devuelve el foco", () => {
    const ui = editor(initial);
    const before = ui.saved();
    const button = ui.rows()[1]._preguntaRefs.quitarBtn;
    button.fire("click");
    assert.equal(ui.modal.visible, true);
    assert.match(ui.elements["quitar-pregunta-advertencia"].textContent, /¿Quitar la pregunta 2\?/);
    assert.equal(ui.elements["cancelar-quitar-pregunta"].focused, true);
    assert.deepEqual(ui.saved(), before);
    ui.modal.hide();
    assert.deepEqual(ui.saved(), before);
    assert.equal(button.focused, true);
    ui.elements["confirmar-quitar-pregunta"].fire("click");
    assert.deepEqual(ui.saved(), before);
});

test("confirmar en el modal quita solo la pregunta elegida y renumera", () => {
    const ui = editor(initial);
    const before = ui.saved();
    ui.rows()[1]._preguntaRefs.quitarBtn.fire("click");
    assert.deepEqual(ui.saved(), before);
    ui.elements["confirmar-quitar-pregunta"].fire("click");
    assert.deepEqual(ui.saved(), [before[0], { ...before[2], orden: 2 }]);
    assert.equal(ui.elements["preguntas-cantidad"].textContent, "2");
    assert.equal(ui.modal.visible, false);
    assert.equal(ui.rows()[0]._preguntaRefs.arrastrar.focused, true);
});

test("el modal advierte sobre preguntas dependientes sin borrarlas al abrir", () => {
    const ui = editor([
        initial[1], { ...initial[2], condicion: { orden: 1, operador: "igual", valor: "si" } },
    ]);
    const before = ui.saved();
    ui.rows()[0]._preguntaRefs.quitarBtn.fire("click");
    assert.match(ui.elements["quitar-pregunta-advertencia"].textContent, /quedarán siempre visibles/);
    assert.deepEqual(ui.saved(), before);
});

test("quitar la última pregunta muestra el vacío y enfoca Agregar pregunta", () => {
    const ui = editor([initial[0]]);
    ui.rows()[0]._preguntaRefs.quitarBtn.fire("click");
    ui.elements["confirmar-quitar-pregunta"].fire("click");
    assert.deepEqual(ui.saved(), []);
    assert.equal(ui.elements["preguntas-vacio-msg"].classList.contains("d-none"), false);
    assert.equal(ui.elements["agregar-pregunta"].focused, true);
});

test("reordenar mueve solo la tarjeta elegida y restaura el scroll si el navegador lo ajusta", () => {
    const ui = editor(initial);
    const row = ui.rows()[2];
    const moved = [];
    ui.elements["preguntas-container"].onInsert = actual => {
        moved.push(actual);
        ui.viewport.scrollY = 0;
    };
    ui.drag(row, ui.rows()[0]);
    assert.deepEqual(moved, [row]);
    assert.equal(ui.viewport.scrollY, 600);
    assert.equal(ui.saved()[0].texto, "Comentarios");
});

test("las flechas recuperan el foco sin desplazar la página", () => {
    const ui = editor(initial);
    const handle = ui.rows()[1]._preguntaRefs.arrastrar;
    handle.fire("keydown", { key: "ArrowUp", preventDefault() {} });
    assert.equal(handle.focusOptions.preventScroll, true);
    assert.equal(ui.viewport.scrollY, 600);
});

test("anima el desplazamiento de las tarjetas y respeta la preferencia de movimiento reducido", () => {
    for (const reduced of [false, true]) {
        const ui = editor(initial);
        const rows = Array.from(ui.rows());
        rows.forEach(row => {
            row.getBoundingClientRect = () => ({ top: ui.rows().indexOf(row) * 300, left: 0 });
        });
        ui.viewport.matchMedia = () => ({ matches: reduced });
        ui.drag(rows[2], rows[0]);
        if (reduced) {
            assert.equal(rows[2].animation, undefined);
        } else {
            assert.match(rows[2].animation.keyframes[0].transform, /translateY\(600px\)/);
            assert.equal(rows[2].animation.options.duration, 180);
        }
    }
});

function startDrag(ui) {
    const handle = ui.rows()[1]._preguntaRefs.arrastrar;
    handle.fire("dragstart", {
        clientX: 25, clientY: 40,
        dataTransfer: { setData() {}, setDragImage() {} },
    });
    return handle;
}

test("acercar al borde desplaza continuamente hacia arriba o abajo sin soltar", () => {
    const ui = editor(initial);
    startDrag(ui);
    ui.doc.fire("dragover", { clientX: 400, clientY: 20, preventDefault() {} });
    ui.tick();
    const first = ui.viewport.scrollY;
    assert.ok(first < 600);
    ui.tick();
    assert.ok(ui.viewport.scrollY < first);
    ui.doc.fire("dragover", { clientX: 400, clientY: 880, preventDefault() {} });
    const before = ui.viewport.scrollY;
    ui.tick();
    assert.ok(ui.viewport.scrollY > before);
    assert.equal(ui.timers.size, 1);
});

test("alejarse del borde detiene el scroll y la velocidad aumenta al acercarse", () => {
    const ui = editor(initial);
    startDrag(ui);
    ui.doc.fire("dragover", { clientX: 400, clientY: 90, preventDefault() {} });
    ui.tick();
    const lento = 600 - ui.viewport.scrollY;
    const before = ui.viewport.scrollY;
    ui.doc.fire("dragover", { clientX: 400, clientY: 10, preventDefault() {} });
    ui.tick();
    assert.ok(before - ui.viewport.scrollY > lento);
    ui.doc.fire("dragover", { clientX: 400, clientY: 450, preventDefault() {} });
    const detenido = ui.viewport.scrollY;
    ui.tick();
    assert.equal(ui.viewport.scrollY, detenido);
    assert.equal(ui.timers.size, 0);
});

test("soltar, cancelar o salir de la ventana limpia el scroll automático", () => {
    for (const event of ["drop", "dragend", "dragleave"]) {
        const ui = editor(initial);
        startDrag(ui);
        ui.doc.fire("dragover", { clientX: 400, clientY: 20, preventDefault() {} });
        ui.doc.fire(event, { relatedTarget: null });
        const before = ui.viewport.scrollY;
        ui.tick();
        assert.equal(ui.timers.size, 0);
        assert.equal(ui.viewport.scrollY, before);
    }
});

test("el scroll del arrastre no se activa para elementos ajenos al editor", () => {
    const ui = editor(initial);
    ui.doc.fire("dragover", { clientX: 400, clientY: 20 });
    assert.equal(ui.timers.size, 0);
    assert.equal(ui.viewport.scrollY, 600);
});

test("mover muestra un toast de tres segundos sin mensaje fijo en el editor", () => {
    const ui = editor(initial);
    ui.drag(ui.rows()[1], ui.rows()[0]);
    assert.equal(ui.notifications.length, 1);
    const toast = ui.notifications[0];
    assert.equal(toast.type, "success");
    assert.equal(toast.message, "Pregunta movida a la posición 1. Guardá la encuesta para conservar el orden.");
    assert.equal(toast.options.timeOut, 3000);
    assert.equal(toast.options.extendedTimeOut, 0);
    assert.equal(toast.options.hideDuration, 0);
    assert.equal(toast.options.positionClass, "toast-bottom-right");
    const template = readFileSync(resolve(__dirname, "../../templates/encuestas/encuesta_form.html"), "utf8");
    assert.doesNotMatch(template, /preguntas-orden-mensaje/);
});
