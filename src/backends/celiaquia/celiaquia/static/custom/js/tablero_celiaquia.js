/* Tablero de seguimiento de Celiaquía.
   Los datos llegan ya agregados por el servidor (json_script "cel-tablero-datos"), sin datos de
   personas. Los filtros de provincia y expediente se aplican acá, sobre esos datos.
   Todo texto que viene de la base se escapa antes de ir al HTML (el número de expediente es
   texto libre cargado por las provincias). */
(function () {
    "use strict";

    const fuente = document.getElementById("cel-tablero-datos");
    const raiz = document.querySelector(".cel-tablero");
    if (!fuente || !raiz || typeof Chart === "undefined") {
        return;
    }
    const DATOS = JSON.parse(fuente.textContent);
    const PROV = DATOS.provincias;
    const EXP = DATOS.expedientes;
    const TRAMOS = DATOS.tramos;
    const URL_EXPEDIENTE = raiz.dataset.urlExpediente || "";
    const EST = {
        CRUCE_FINALIZADO: "Cruce finalizado",
        CONFIRMACION_DE_ENVIO: "Confirmación de envío",
        ASIGNADO: "Asignado",
        EN_ESPERA: "En espera",
        CREADO: "Creado",
        PROCESADO: "Procesado",
        RECEPCIONADO: "Recepcionado",
        PROCESO_DE_CRUCE: "Proceso de cruce",
    };

    /* ---------- Utilidades ---------- */
    const nf = new Intl.NumberFormat("es-AR");
    const fmt = (n) => nf.format(n);
    const pct = (a, b, d = 1) => (b ? (100 * a / b).toFixed(d).replace(".", ",") + " %" : "—");
    const sum = (rows, k) => rows.reduce((s, r) => s + r[k], 0);
    const esc = (texto) => String(texto == null ? "" : texto).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[c]);
    const C = {
        teal: "#3b8681", ambar: "#e7a13a", rojo: "#e5534b", gris: "#8a94a8", azul: "#8fa6d6", track: "#2f3d61",
        grilla: "rgba(255,255,255,.08)", gris2: "#c3cad8", sobreClaro: "#1c1c1c", tooltip: "#1c2440",
        borde: "#232d4f", sobreAzul: "#0b1424",
        escala: ["#2a3b5e", "#1f4b48", "#2f6b67", "#3b8681", "#6fb3ac"],
        escalaTexto: (i) => (i === 4 ? "#0b0b0b" : "#fff"),
        vacio: ["#2a3658", "#8a94a8"],
    };
    const sumarCat = (P, rows) => {
        const t = {};
        rows.forEach((r) => Object.entries(P[r.p] || {}).forEach(([k, v]) => {
            t[k] = (t[k] || 0) + v;
        }));
        return Object.entries(t).sort((a, b) => b[1] - a[1]);
    };
    const state = { prov: "", exp: "", expTodos: false };
    const charts = {};
    const tables = {};
    const rowsInScope = () => (state.prov ? PROV.filter((r) => r.p === state.prov) : PROV);

    // Expedientes de la provincia elegida, con las filas del mismo id juntas (un expediente
    // puede tener ciudadanos de dos provincias).
    const CAMPOS_EXP = ["leg", "pend", "apr", "rech", "sub", "match", "nomatch", "sincruce", "tit", "susp", "fuera"];
    function expedientesEnAlcance() {
        const m = new Map();
        EXP.filter((e) => !state.prov || e.p === state.prov).forEach((e) => {
            const x = m.get(e.id);
            if (!x) {
                m.set(e.id, Object.assign({}, e, { provs: [e.p] }));
                return;
            }
            CAMPOS_EXP.forEach((k) => {
                x[k] += e[k];
            });
            x.provs.push(e.p);
        });
        return [...m.values()].map((x) => Object.assign(x, { p: x.provs.join(" + "), porResolver: x.pend + x.sub }));
    }
    // Con un expediente elegido, tarjetas y circuito usan una sola fila con la forma de PROV.
    function rowsDetalle() {
        const e = state.exp && expedientesEnAlcance().find((x) => String(x.id) === state.exp);
        if (!e) {
            return null;
        }
        return [Object.assign({}, e, { exp: 1, expProc: e.est === "CRUCE_FINALIZADO" ? 0 : 1, per: e.leg, cupo: 0 })];
    }

    /* ---------- Chart.js: valores por defecto y etiquetas sobre las barras ---------- */
    Chart.defaults.font.family = "Roboto, \"Segoe UI\", sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = C.gris2;
    // Escribe el valor dentro de cada barra horizontal cuando entra; si no, queda en el tooltip y la tabla.
    const etiquetas = {
        id: "celEtiquetas",
        afterDatasetsDraw(chart, args, opts) {
            if (!opts || !opts.formato) {
                return;
            }
            const { ctx } = chart;
            ctx.save();
            ctx.font = "500 11px Roboto, \"Segoe UI\", sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            chart.data.datasets.forEach((ds, i) => {
                const meta = chart.getDatasetMeta(i);
                if (meta.hidden) {
                    return;
                }
                meta.data.forEach((el, j) => {
                    const txt = opts.formato(ds.data[j], i, j);
                    if (!txt) {
                        return;
                    }
                    const { x, y, base } = el.getProps(["x", "y", "base"], true);
                    if (ctx.measureText(txt).width + 10 > Math.abs(x - base)) {
                        return;
                    }
                    ctx.fillStyle = (opts.color && opts.color(i, j)) || "#fff";
                    ctx.fillText(txt, (x + base) / 2, y);
                });
            });
            ctx.restore();
        },
    };

    function leyenda(id, items) {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = items.map(([n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("");
        }
    }
    function alto(id, filas, porFila = 34, extra = 30) {
        document.getElementById(`ch-${id}`).parentElement.style.height = `${Math.max(120, filas * porFila + extra)}px`;
    }
    function refrescarTabla(id) {
        const wrap = raiz.querySelector(`[data-id="${id}"] .cel-tblwrap`);
        if (!wrap || wrap.classList.contains("cel-oculto")) {
            return;
        }
        const t = tables[id];
        wrap.innerHTML = `<table class="cel-tabla"><thead><tr>${t.head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>`
            + t.rows.map((r) => `<tr>${r.map((c) => `<td>${typeof c === "number" ? fmt(c) : esc(c)}</td>`).join("")}</tr>`).join("")
            + "</tbody></table>";
    }
    function dibujar(id, config, tabla) {
        if (charts[id]) {
            charts[id].destroy();
        }
        config.plugins = [etiquetas];
        config.options = Object.assign({ animation: false, maintainAspectRatio: false }, config.options);
        config.options.plugins = Object.assign({ legend: { display: false } }, config.options.plugins);
        config.options.plugins.tooltip = Object.assign({ backgroundColor: C.tooltip, padding: 10 }, config.options.plugins.tooltip);
        charts[id] = new Chart(document.getElementById(`ch-${id}`), config);
        tables[id] = tabla;
        refrescarTabla(id);
    }
    // Ejes horizontales sin números (el valor va en la barra) que terminan en el dato máximo.
    const ejeX = (max, extra = {}) => Object.assign({
        beginAtZero: true, max, grid: { color: C.grilla }, border: { display: false }, ticks: { display: false },
    }, extra);
    const ejeY = { grid: { display: false }, border: { display: false }, ticks: { font: { size: 12 } } };
    const barra = (label, data, color, extra = {}) => Object.assign({
        label, data, backgroundColor: color, borderColor: C.borde, borderWidth: 1, borderRadius: 3,
        borderSkipped: false, barPercentage: 0.8, categoryPercentage: 0.8, maxBarThickness: 26,
    }, extra);
    const detalle = (quedan) => quedan.filter((x) => x[1]).map(([n, v]) => `${fmt(v)} ${n}`).join(" · ");

    /* ---------- Tarjetas con cuadrícula 10 x 10 (SVG) ---------- */
    function drawKpis(rows) {
        const g = (k) => sum(rows, k);
        const leg = g("leg");
        const apr = g("apr");
        const tit = g("tit");
        const exp = g("exp");
        const expProc = g("expProc");
        // Mayor resto: los cuadraditos suman lo que representan.
        const reparto = (segs, total, celdas) => {
            const raw = segs.map((s) => celdas * s[1] / total);
            const base = raw.map(Math.floor);
            let falta = Math.round(celdas * segs.reduce((a, s) => a + s[1], 0) / total) - base.reduce((a, b) => a + b, 0);
            raw.map((v, i) => [v - base[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => {
                if (falta > 0) {
                    base[i] += 1;
                    falta -= 1;
                }
            });
            return base;
        };
        const CEL = 12;
        const SEP = 3;
        const LADO = 10 * CEL + 9 * SEP;
        const waffle = (segs, total, celdas = 100) => {
            const n = total ? reparto(segs, total, celdas) : segs.map(() => 0);
            const seq = [];
            segs.forEach((s, i) => {
                for (let j = 0; j < n[i]; j += 1) {
                    seq.push(s);
                }
            });
            let r = "";
            for (let i = 0; i < 100; i += 1) {
                const x = (i % 10) * (CEL + SEP);
                const y = (9 - Math.floor(i / 10)) * (CEL + SEP);
                const s = seq[i];
                if (!s) {
                    r += `<rect x="${x}" y="${y}" width="${CEL}" height="${CEL}" rx="2" fill="${C.track}"/>`;
                } else if (s[3]) {
                    r += `<rect x="${x + 1}" y="${y + 1}" width="${CEL - 2}" height="${CEL - 2}" rx="1.5" fill="none" stroke="${s[2]}" stroke-width="2"/>`;
                } else {
                    r += `<rect x="${x}" y="${y}" width="${CEL}" height="${CEL}" rx="2" fill="${s[2]}"/>`;
                }
            }
            const etiqueta = segs.map((s) => `${s[0]}: ${fmt(s[1])}`).join(", ");
            return `<svg class="cel-waffle" width="${LADO}" height="${LADO}" viewBox="0 0 ${LADO} ${LADO}" role="img" aria-label="${etiqueta}">${r}</svg>`;
        };
        const ley = (segs, total) => `<ul class="cel-ley">${segs.map((s) => {
            const marca = s[3] ? `border:2px solid ${s[2]}` : `background:${s[2]}`;
            return `<li><i style="${marca}"></i><span>${s[0]}</span><b>${fmt(s[1])}</b><em>${pct(s[1], total, 0)}</em></li>`;
        }).join("")}</ul>`;
        const card = (valor, titulo, waf, l, pie) => `<div class="cel-kpi"><div class="cel-kpi-cabeza"><b>${valor}</b><span>${titulo}</span></div>`
            + `<div class="cel-kpi-fila">${waf}${l}</div><div class="cel-kpi-pie">${pie}</div></div>`;
        const sExp = [["Cruce finalizado", exp - expProc, C.azul], ["En proceso", expProc, C.gris]];
        const sPer = [["Aprobadas", apr, C.teal], ["A subsanar", g("sub"), C.ambar], ["Rechazadas", g("rech"), C.rojo], ["Pendientes", g("pend"), C.gris]];
        const sTit = [["Titulares", tit, C.azul], ["No llegan", apr - tit, C.teal, true]];
        const cupo = g("cupo");
        const fuera = g("fuera");
        document.getElementById("cel-kpis").innerHTML =
            card(fmt(exp), "Expedientes", waffle(sExp, 1, 1), ley(sExp, exp),
                `Cada cuadradito es un expediente · ${exp ? Math.round(leg / exp) : 0} personas por expediente en promedio`)
            + card(fmt(leg), "Personas cargadas", waffle(sPer, leg), ley(sPer, leg),
                "Cada cuadradito es el 1 % · estado de la revisión técnica · sin responsables")
            + card(fmt(tit), "Titulares", waffle(sTit, leg), ley(sTit, leg),
                `No llegan: ${fmt(apr - tit)} aprobadas que no son titulares (${fmt(g("nomatch"))} sin coincidencia SINTyS · ${fmt(g("sincruce"))} sin cruzar`
                + `${fuera ? ` · ${fmt(fuera)} fuera de cupo` : ""}) · cupo usado ${pct(tit, cupo, 0)}`);
    }

    /* ---------- Gráficos ---------- */
    function drawCupo(rows) {
        const r = [...rows].sort((a, b) => b.tit - a.tit || b.cupo - a.cupo);
        leyenda("ley-cupo", [["Usado (titulares)", C.teal], ["Disponible", C.track]]);
        alto("cupo", r.length);
        dibujar("cupo", {
            type: "bar",
            data: {
                labels: r.map((x) => x.p),
                datasets: [
                    barra("Usado", r.map((x) => x.tit), C.teal, { stack: "s" }),
                    barra("Disponible", r.map((x) => Math.max(0, x.cupo - x.tit)), C.track, { stack: "s" }),
                ],
            },
            options: {
                indexAxis: "y",
                scales: { x: ejeX(Math.max(1, ...r.map((x) => Math.max(x.cupo, x.tit))), { stacked: true }), y: Object.assign({ stacked: true }, ejeY) },
                plugins: {
                    celEtiquetas: { formato: (v, i, j) => (i === 0 && v && r[j].cupo ? pct(r[j].tit, r[j].cupo, 0) : "") },
                    tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw)}${c.datasetIndex === 0 ? ` · ${pct(c.raw, r[c.dataIndex].cupo)} del cupo` : ""}` } },
                },
            },
        }, { head: ["Provincia", "Cupo asignado", "Titulares", "Disponible", "% usado"], rows: r.map((x) => [x.p, x.cupo, x.tit, x.cupo - x.tit, pct(x.tit, x.cupo)]) });
    }

    function drawPiramide(rows) {
        const P = DATOS.piramide;
        const F = TRAMOS.map((t, i) => rows.reduce((s, r) => s + (P[r.p] ? P[r.p].F[i] : 0), 0));
        const M = TRAMOS.map((t, i) => rows.reduce((s, r) => s + (P[r.p] ? P[r.p].M[i] : 0), 0));
        const TOT = F.map((v, i) => v + M[i]);
        leyenda("ley-piramide", [["Mujeres", C.teal], ["Varones", C.azul]]);
        alto("piramide", TRAMOS.length, 32);
        dibujar("piramide", {
            type: "bar",
            data: {
                labels: TRAMOS.map((t, i) => `${t} · ${fmt(TOT[i])}`),
                datasets: [barra("Mujeres", F, C.teal, { stack: "s" }), barra("Varones", M, C.azul, { stack: "s" })],
            },
            options: {
                indexAxis: "y",
                scales: { x: ejeX(Math.max(1, ...TOT), { stacked: true }), y: Object.assign({ stacked: true }, ejeY) },
                plugins: {
                    celEtiquetas: { formato: (v) => (v ? fmt(v) : ""), color: (i) => (i === 1 ? C.sobreAzul : "#fff") },
                    tooltip: {
                        callbacks: {
                            title: (c) => `${TRAMOS[c[0].dataIndex]} años · ${fmt(TOT[c[0].dataIndex])} titulares`,
                            label: (c) => `${c.dataset.label}: ${fmt(c.raw)} · ${pct(c.raw, TOT[c.dataIndex], 0)}`,
                        },
                    },
                },
            },
        }, { head: ["Tramo", "Mujeres", "Varones", "Total"], rows: TRAMOS.map((t, i) => [t, F[i], M[i], TOT[i]]) });
    }

    function drawEmbudo(rows) {
        const g = (k) => sum(rows, k);
        const st = [
            { n: "Cargados", sigue: g("leg"), quedan: [] },
            { n: "Revisión técnica", sigue: g("apr"), quedan: [["a subsanar", g("sub")], ["rechazadas", g("rech")], ["pendientes de revisar", g("pend")]] },
            { n: "Cruce SINTyS", sigue: g("match"), quedan: [["sin coincidencia", g("nomatch")], ["todavía sin cruzar", g("sincruce")]] },
            { n: "Cupo provincial", sigue: g("tit"), quedan: [["fuera de cupo", g("fuera")], ["suspendidos", g("susp")]] },
        ];
        st.forEach((s) => {
            s.q = s.quedan.reduce((a, x) => a + x[1], 0);
        });
        const base = st[0].sigue;
        leyenda("ley-embudo", [["Siguen", C.azul], ["Se quedan en este paso", C.gris]]);
        alto("embudo", st.length, 38);
        dibujar("embudo", {
            type: "bar",
            data: {
                labels: st.map((s) => s.n),
                datasets: [barra("Siguen", st.map((s) => s.sigue), C.azul, { stack: "s" }), barra("Se quedan", st.map((s) => s.q), C.gris, { stack: "s" })],
            },
            options: {
                indexAxis: "y",
                scales: { x: ejeX(Math.max(1, base), { stacked: true }), y: Object.assign({ stacked: true }, ejeY) },
                plugins: {
                    celEtiquetas: {
                        formato: (v, i) => {
                            if (!v) {
                                return "";
                            }
                            return i === 0 ? `${fmt(v)} · ${pct(v, base, 0)}` : fmt(v);
                        },
                        color: (i) => (i === 0 ? C.sobreAzul : "#fff"),
                    },
                    tooltip: {
                        callbacks: {
                            label: (c) => (c.datasetIndex === 0
                                ? `Siguen: ${fmt(c.raw)} · ${pct(c.raw, base, 0)} de los cargados`
                                : `Se quedan: ${detalle(st[c.dataIndex].quedan) || "—"}`),
                        },
                    },
                },
            },
        }, {
            head: ["Paso", "Siguen", "% de cargados", "Se quedan", "Detalle"],
            rows: st.map((s) => [s.n, s.sigue, pct(s.sigue, base), s.q, detalle(s.quedan) || "—"]),
        });
        document.getElementById("cel-perdidas").innerHTML = st.slice(1).map((s) => `<li><strong>${s.n}:</strong> se quedan ${fmt(s.q)}${s.q ? ` (${detalle(s.quedan)})` : ""}</li>`).join("");
    }

    function drawConversion(rows) {
        const r = [...rows].sort((a, b) => b.leg - a.leg);
        const etapas = [
            ["Carga → aprobado", (x) => [x.apr, x.leg]],
            ["Aprobado → validado SINTyS", (x) => [x.match, x.apr]],
            ["Validado SINTyS → titular", (x) => [x.tit, x.match]],
        ];
        const celda = (a, b) => {
            if (!b) {
                return `<td class="v" style="background:${C.vacio[0]};color:${C.vacio[1]}">—</td>`;
            }
            const v = Math.round(100 * a / b);
            const i = Math.min(4, Math.floor(v / 20));
            return `<td class="v" style="background:${C.escala[i]};color:${C.escalaTexto(i)}" title="${fmt(a)} de ${fmt(b)}">${v} %</td>`;
        };
        document.getElementById("ch-conversion").innerHTML = `<table class="cel-calor"><thead><tr><th></th>${etapas.map((e) => `<th>${e[0]}</th>`).join("")}</tr></thead><tbody>`
            + r.map((x) => `<tr><td>${esc(x.p)}</td>${etapas.map(([, f]) => celda(...f(x))).join("")}</tr>`).join("") + "</tbody></table>";
        tables.conversion = {
            head: ["Provincia", ...etapas.map((e) => e[0])],
            rows: r.map((x) => [x.p, ...etapas.map(([, f]) => {
                const [a, b] = f(x);
                return pct(a, b, 0);
            })]),
        };
        refrescarTabla("conversion");
    }

    function drawRevision(rows) {
        const r = [...rows].sort((a, b) => b.leg - a.leg);
        const S = [["Aprobadas", "apr", C.teal], ["A subsanar", "sub", C.ambar], ["Rechazadas", "rech", C.rojo], ["Pendientes", "pend", C.gris]];
        leyenda("ley-revision", S.map((s) => [s[0], s[2]]));
        alto("revision", r.length, 30);
        dibujar("revision", {
            type: "bar",
            data: { labels: r.map((x) => x.p), datasets: S.map(([n, k, c]) => barra(n, r.map((x) => (x.leg ? 100 * x[k] / x.leg : 0)), c, { stack: "s" })) },
            options: {
                indexAxis: "y",
                scales: { x: ejeX(100, { stacked: true }), y: Object.assign({ stacked: true }, ejeY) },
                plugins: {
                    celEtiquetas: { formato: (v) => (v >= 8 ? `${Math.round(v)} %` : ""), color: (i) => (i === 1 ? C.sobreClaro : "#fff") },
                    tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(r[c.dataIndex][S[c.datasetIndex][1]])} · ${Math.round(c.raw)} %` } },
                },
            },
        }, {
            head: ["Provincia", "Beneficiarios", ...S.map((s) => s[0])],
            rows: r.map((x) => [x.p, x.leg, ...S.map((s) => `${fmt(x[s[1]])} (${pct(x[s[1]], x.leg, 0)})`)]),
        });
    }

    function drawBarrasSimples(id, data, unidad, color) {
        const wrap = document.getElementById(`ch-${id}`).parentElement;
        const canvas = wrap.querySelector("canvas");
        const vacio = wrap.querySelector(".cel-vacio");
        if (!data.length) {
            if (charts[id]) {
                charts[id].destroy();
                delete charts[id];
            }
            wrap.style.height = "auto";
            canvas.classList.add("cel-oculto");
            if (!vacio) {
                wrap.insertAdjacentHTML("beforeend", `<p class="cel-vacio">Sin ${unidad} para el filtro elegido.</p>`);
            }
            tables[id] = { head: ["Categoría", unidad], rows: [] };
            return;
        }
        canvas.classList.remove("cel-oculto");
        if (vacio) {
            vacio.remove();
        }
        alto(id, data.length, 30);
        dibujar(id, {
            type: "bar",
            data: { labels: data.map((d) => `${d[0]} · ${fmt(d[1])}`), datasets: [barra(unidad, data.map((d) => d[1]), color)] },
            options: {
                indexAxis: "y",
                scales: { x: ejeX(Math.max(...data.map((d) => d[1]))), y: ejeY },
                plugins: { tooltip: { callbacks: { label: (c) => `${fmt(c.raw)} ${unidad}` } } },
            },
        }, { head: ["Categoría", unidad], rows: data.map((d) => [d[0], d[1]]) });
    }

    /* ---------- Ranking de expedientes ---------- */
    function drawExpedientes() {
        const todos = expedientesEnAlcance().sort((a, b) => b.porResolver - a.porResolver || b.leg - a.leg);
        const lista = state.expTodos ? todos : todos.slice(0, 10);
        const S = [["Aprobadas", "apr", C.teal], ["A subsanar", "sub", C.ambar], ["Rechazadas", "rech", C.rojo], ["Pendientes", "pend", C.gris]];
        leyenda("ley-expedientes", S.map((s) => [s[0], s[2]]));
        const mix = (e) => `<div class="cel-mix" title="${S.map((s) => `${s[0]}: ${fmt(e[s[1]])}`).join(" · ")}">`
            + S.map((s) => (e[s[1]] ? `<i style="width:${100 * e[s[1]] / e.leg}%;background:${s[2]}"></i>` : "")).join("") + "</div>";
        const tabla = document.getElementById("tbl-expedientes");
        tabla.innerHTML = "<thead><tr><th>Expediente</th><th>Provincia</th><th>Estado</th><th>Días</th><th>Beneficiarios</th>"
            + "<th>Revisión técnica</th><th>Por resolver</th><th>Rechazadas</th><th>Titulares</th></tr></thead><tbody>"
            + lista.map((e) => `<tr data-exp="${e.id}" class="${String(e.id) === state.exp ? "sel" : ""}">`
                + `<td class="cel-exp-id"><b>#${e.id}</b><small title="${esc(e.n)}">${e.n ? `cargado como «${esc(e.n)}»` : "sin número cargado"}</small></td>`
                + `<td>${esc(e.p)}</td><td>${esc(EST[e.est] || e.est)}</td><td>${fmt(e.d)}</td><td>${fmt(e.leg)}</td><td>${mix(e)}</td>`
                + `<td><b>${fmt(e.porResolver)}</b></td><td>${fmt(e.rech)}</td><td>${fmt(e.tit)} <small>(${pct(e.tit, e.leg, 0)})</small></td></tr>`).join("")
            + "</tbody>";
        tabla.querySelectorAll("tbody tr").forEach((tr) => tr.addEventListener("click", () => {
            state.exp = state.exp === tr.dataset.exp ? "" : tr.dataset.exp;
            applyScope();
        }));
        const btn = document.getElementById("cel-expedientes-todos");
        btn.classList.toggle("cel-oculto", todos.length <= 10);
        btn.textContent = state.expTodos ? "Ver los 10 primeros" : `Ver todos (${todos.length})`;
        // Por qué el id y no el número: cuántos no tienen número y cuántos lo comparten con otro.
        const usos = {};
        todos.forEach((e) => {
            if (e.n) {
                usos[e.n] = (usos[e.n] || 0) + 1;
            }
        });
        const sinNro = todos.filter((e) => !e.n).length;
        const repetido = todos.filter((e) => e.n && usos[e.n] > 1).length;
        document.getElementById("cel-nota-expedientes").textContent = (sinNro || repetido)
            ? `De ${fmt(todos.length)} expedientes, ${fmt(sinNro)} no tienen número cargado y ${fmt(repetido)} comparten el número con otro: por eso se identifican por el id de SISOC.`
            : "";
    }

    /* ---------- Filtros ---------- */
    const fProv = document.getElementById("cel-filtro-provincia");
    const fExp = document.getElementById("cel-filtro-expediente");

    function llenarExpedientes() {
        const lista = expedientesEnAlcance().sort((a, b) => a.p.localeCompare(b.p) || b.id - a.id);
        if (state.exp && !lista.some((e) => String(e.id) === state.exp)) {
            state.exp = "";
        }
        fExp.innerHTML = `<option value="">Todos (${fmt(lista.length)})</option>`
            + lista.map((e) => `<option value="${e.id}">#${e.id} · ${esc(e.p)} · ${fmt(e.leg)} benef.</option>`).join("");
        fExp.value = state.exp;
    }

    function drawAll() {
        const rows = rowsInScope();
        const det = rowsDetalle() || rows;
        drawKpis(det);
        drawCupo(rows);
        drawPiramide(rows);
        drawEmbudo(det);
        drawConversion(rows);
        drawExpedientes();
        drawRevision(rows);
        const rech = sumarCat(DATOS.rechazo, rows);
        const subs = sumarCat(DATOS.subsanacion, rows);
        const err = sumarCat(DATOS.errores, rows);
        drawBarrasSimples("rechazo", rech, "rechazadas", C.rojo);
        drawBarrasSimples("subsanacion", subs, "observaciones", C.ambar);
        drawBarrasSimples("errores", err, "filas", C.gris2);
        const tot = (d) => d.reduce((a, x) => a + x[1], 0);
        const de = (d, k) => (d.find((x) => x[0] === k) || [0, 0])[1];
        // Las barras de rechazo cuentan menciones: una rechazada puede tener dos motivos.
        const nRech = sum(rows, "rech");
        document.getElementById("cel-nota-rechazo").textContent = tot(rech)
            ? `${fmt(de(rech, "Sin motivo registrado"))} de ${fmt(nRech)} rechazadas no tienen motivo registrado. `
                + `Una rechazada puede mencionar más de un motivo: las barras suman ${fmt(tot(rech))}.`
            : "";
        document.getElementById("cel-nota-subsanacion").textContent = tot(subs)
            ? `El ${pct(de(subs, "Otros"), tot(subs), 0)} cae en "Otros": el tipo no alcanza para clasificar.`
            : "";
        document.getElementById("cel-nota-errores").textContent = tot(err)
            ? `"Corregido o sin mensaje": SISOC borra el mensaje cuando el registro se corrige o se procesa (${fmt(de(err, "Corregido o sin mensaje"))} de ${fmt(tot(err))}).`
            : "";
    }

    function applyScope() {
        state.prov = fProv.value;
        llenarExpedientes();
        const rows = rowsInScope();
        const det = rowsDetalle();
        document.getElementById("cel-chip-alcance").textContent = (state.prov || "Todas las provincias") + (det ? ` · expediente #${state.exp}` : "");
        document.getElementById("cel-chip-casos").textContent = `${fmt(sum(det || rows, "leg"))} personas cargadas`;
        const aviso = document.getElementById("cel-aviso-expediente");
        aviso.classList.toggle("cel-oculto", !det);
        if (det) {
            const e = det[0];
            const url = URL_EXPEDIENTE.replace(/\/0\/$/, `/${e.id}/`);
            aviso.innerHTML = `<b>Expediente #${e.id}</b> (${esc(e.p)} · ${esc(EST[e.est] || e.est)} · creado hace ${fmt(e.d)} días): `
                + `las tarjetas y el circuito muestran solo este expediente; el resto de los bloques sigue mostrando ${esc(state.prov || "todas las provincias")}.`
                + `<a href="${esc(url)}">Abrir en SISOC</a><a href="#" id="cel-quitar-expediente">Quitar filtro</a>`;
            document.getElementById("cel-quitar-expediente").addEventListener("click", (ev) => {
                ev.preventDefault();
                state.exp = "";
                applyScope();
            });
        }
        drawAll();
    }

    /* ---------- Inicio ---------- */
    fProv.innerHTML = "<option value=\"\">Todas las provincias</option>"
        + [...PROV].sort((a, b) => a.p.localeCompare(b.p)).map((r) => `<option value="${esc(r.p)}">${esc(r.p)}</option>`).join("");
    fProv.addEventListener("change", () => {
        state.exp = "";
        applyScope();
    });
    fExp.addEventListener("change", () => {
        state.exp = fExp.value;
        applyScope();
    });
    document.getElementById("cel-expedientes-todos").addEventListener("click", () => {
        state.expTodos = !state.expTodos;
        drawExpedientes();
    });
    raiz.querySelectorAll(".cel-btn-tabla[type=button]").forEach((b) => {
        const sec = b.closest(".cel-seccion");
        const wrap = sec && sec.querySelector(".cel-tblwrap");
        if (!wrap) {
            return;
        }
        b.addEventListener("click", () => {
            const ch = sec.querySelector(".cel-chart");
            const ver = wrap.classList.contains("cel-oculto");
            wrap.classList.toggle("cel-oculto", !ver);
            if (ch) {
                ch.classList.toggle("cel-oculto", ver);
            }
            b.textContent = ver ? "Gráfico" : "Tabla";
            if (ver) {
                refrescarTabla(sec.dataset.id);
            }
        });
    });
    applyScope();
}());
