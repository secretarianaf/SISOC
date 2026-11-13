/* Tablero Becas Progresar · Curso obligatorio.
   Los datos llegan ya agregados y recortados al alcance del usuario por el servidor
   (json_script "tpc-tablero-datos"), sin datos de personas: filas de las tablas
   bi_progresar_curso_obligatorio_resumen y _evolucion. Los filtros de jurisdicción y
   línea se aplican acá, sobre esos datos. Los nombres que vienen de la base se escapan. */
(function () {
    "use strict";

    const fuente = document.getElementById("tpc-tablero-datos");
    const raiz = document.querySelector(".tpc-tablero");
    if (!fuente || !raiz || typeof Chart === "undefined") {
        return;
    }
    const T = JSON.parse(fuente.textContent);

    /* ---------- Utilidades ---------- */
    const nf = new Intl.NumberFormat("es-AR");
    const fmt = (n) => nf.format(n);
    const dec = (n, d = 1) => n.toFixed(d).replace(".", ",");
    const pct = (a, b, d = 1) => (b ? `${dec(100 * a / b, d)} %` : "—");
    const esc = (texto) => String(texto == null ? "" : texto).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[c]);
    const suma = (rows, f, col) => rows.reduce((s, r) => s + (f(r) ? r[col] : 0), 0);
    const fechaLarga = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
    const C = {
        teal: "#3b8681", tealClaro: "#6fb3ac", ambar: "#e7a13a", rojo: "#e5534b", gris: "#8a94a8",
        azul: "#8fa6d6", track: "#2f3d61", grilla: "rgba(255,255,255,.08)", gris2: "#c3cad8",
        tooltip: "#1c2440", borde: "#232d4f", sobreAzul: "#0b1424", sobreClaro: "#0b1424",
    };

    /* ---------- Catálogos ---------- */
    const LINEAS = ["Progresar Obligatorio", "Progresar Superior", "Progresar Trabajo"];
    const LINEA_DEF = "Progresar Obligatorio";
    const ESTADOS = ["Certificado", "Aprobó sin certificado", "Rindió y no aprobó", "Inscripto sin rendir"];
    const RINDIERON = ["Certificado", "Aprobó sin certificado", "Rindió y no aprobó"];
    const APROBARON = ["Certificado", "Aprobó sin certificado"];
    const RANGOS = ["15 a 17", "18", "19 y 20", "21 a 24", "25 o más"];
    const GENEROS = [["F", "Mujeres"], ["M", "Varones"], ["X", "X"]];
    const colEstado = (e) => ({
        Certificado: C.teal, "Aprobó sin certificado": C.tealClaro, "Rindió y no aprobó": C.rojo, "Inscripto sin rendir": C.ambar,
    })[e];
    const colGenero = (g) => ({ F: C.teal, M: C.azul, X: C.gris })[g];

    /* ---------- De las tablas a lo que usan los gráficos ----------
       cubo:   [provincia_id, línea, estado, género, rango, titulares, suma de edades, casos con edad]
       trab:   [provincia_id, línea, género, tramo de inactividad, titulares]
       tiempo: [provincia_id, línea, género, tramo hasta aprobar, titulares]
       evol:   [provincia_id, línea, género, fecha, inscriptos, aprobados] */
    function desdeTablas(datos) {
        const R = datos.resumen_columnas;
        const E = datos.evolucion_columnas;
        const [pr, li, es, ge, ra, ti, ta, n, se, ne] = ["provincia_id", "linea", "estado_curso", "genero_codigo",
            "rango_edad", "tramo_inactividad", "tramo_aprobacion", "titulares", "suma_edad", "casos_edad"].map((c) => R.indexOf(c));
        const [ef, ep, el, eg, ei, ea] = ["fecha", "provincia_id", "linea", "genero_codigo", "inscriptos", "aprobados"]
            .map((c) => E.indexOf(c));
        return {
            cubo: datos.resumen.map((r) => [r[pr], r[li], r[es], r[ge], r[ra], r[n], r[se] || 0, r[ne]]),
            trab: datos.resumen.filter((r) => r[ti] !== null).map((r) => [r[pr], r[li], r[ge], r[ti], r[n]]),
            tiempo: datos.resumen.filter((r) => r[ta] !== null).map((r) => [r[pr], r[li], r[ge], r[ta], r[n]]),
            evol: datos.evolucion.map((r) => [r[ep], r[el], r[eg], r[ef], r[ei], r[ea]]),
        };
    }
    const D = desdeTablas(T);
    const PROVS = T.provincias;   // { id: nombre }, solo las del alcance del usuario
    const nomProv = (id) => esc(PROVS[id] || `Sin dato (${id})`);
    const IDS = Object.keys(PROVS).sort((a, b) => PROVS[a].localeCompare(PROVS[b]));
    const PROVINCIAL = T.alcance === "provincial";
    const provDefecto = () => (PROVINCIAL && IDS.length === 1 ? IDS[0] : "");

    const state = { prov: provDefecto(), linea: LINEA_DEF };
    const charts = {};
    const tables = {};
    const enLinea = (r) => !state.linea || r[1] === state.linea;
    const enAlcance = (r) => (!state.prov || String(r[0]) === state.prov) && enLinea(r);

    /* ---------- Chart.js ---------- */
    Chart.defaults.font.family = 'Roboto, "Segoe UI", sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.color = C.gris2;
    Chart.defaults.animation = false;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.backgroundColor = C.tooltip;
    const etiquetas = {   // valor dentro de la barra cuando entra
        id: "tpcEtiquetas",
        afterDatasetsDraw(chart, args, opts) {
            if (!opts || !opts.formato) {
                return;
            }
            const { ctx } = chart;
            const horiz = chart.options.indexAxis === "y";
            ctx.save();
            ctx.font = '500 11px Roboto, "Segoe UI", sans-serif';
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            chart.data.datasets.forEach((ds, i) => {
                const meta = chart.getDatasetMeta(i);
                if (meta.hidden || meta.type !== "bar") {
                    return;
                }
                meta.data.forEach((elem, j) => {
                    const txt = opts.formato(ds.data[j], i, j);
                    if (!txt) {
                        return;
                    }
                    const { x, y, base, width, height } = elem.getProps(["x", "y", "base", "width", "height"], true);
                    const largo = horiz ? Math.abs(x - base) : Math.abs(y - base);
                    const ancho = horiz ? height : width;
                    const noEntra = horiz ? ctx.measureText(txt).width + 10 > largo
                        : (largo < 18 || ctx.measureText(txt).width + 4 > ancho);
                    if (noEntra) {
                        return;
                    }
                    ctx.fillStyle = (opts.color && opts.color(i, j)) || "#fff";
                    if (horiz) {
                        ctx.fillText(txt, (x + base) / 2, y);
                    } else {
                        ctx.fillText(txt, x, y + 10);
                    }
                });
            });
            ctx.restore();
        },
    };
    Chart.register(etiquetas);

    function leyenda(id, items) {
        document.getElementById(id).innerHTML = items
            .map(([n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("");
    }
    function alto(id, px) {
        document.getElementById(`ch-${id}`).parentElement.style.height = `${Math.max(140, px)}px`;
    }
    function refrescarTabla(id) {
        const wrap = raiz.querySelector(`[data-id="${id}"] .tpc-tblwrap`);
        if (!wrap || wrap.classList.contains("tpc-oculto") || !tables[id]) {
            return;
        }
        const t = tables[id];
        wrap.innerHTML = `<table class="tpc-tabla"><thead><tr>${t.head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${
            t.rows.map((r) => `<tr>${r.map((c) => `<td>${typeof c === "number" ? fmt(c) : c}</td>`).join("")}</tr>`).join("")
        }</tbody></table>`;
    }
    function dibujar(id, config, tabla) {
        if (charts[id]) {
            charts[id].destroy();
        }
        charts[id] = new Chart(document.getElementById(`ch-${id}`), config);
        tables[id] = tabla;
        refrescarTabla(id);
    }
    const ejeOculto = (max, extra = {}) => Object.assign({
        beginAtZero: true, max, grid: { color: C.grilla }, border: { display: false }, ticks: { display: false },
    }, extra);
    const ejeCat = () => ({ grid: { display: false }, border: { display: false }, ticks: { font: { size: 12 } } });
    const barra = (label, data, color, extra = {}) => Object.assign({
        label, data, backgroundColor: color, borderColor: C.borde, borderWidth: 1, borderRadius: 3,
        borderSkipped: false, barPercentage: 0.8, categoryPercentage: 0.8, maxBarThickness: 26,
    }, extra);

    /* ---------- Tarjetas principales ---------- */
    function drawKpis() {
        const cubo = D.cubo.filter(enAlcance);
        const n = (f) => suma(cubo, f, 5);
        const est = (e) => n((r) => r[2] === e);
        const padron = n(() => true);
        const ins = n((r) => r[2] !== "No inscripto");
        const rind = n((r) => RINDIERON.includes(r[2]));
        const apr = n((r) => APROBARON.includes(r[2]));
        const edadS = suma(cubo, (r) => r[2] !== "No inscripto", 6);
        const edadN = suma(cubo, (r) => r[2] !== "No inscripto", 7);
        const reparto = (segs, total) => {
            const raw = segs.map((s) => 100 * s[1] / total);
            const base = raw.map(Math.floor);
            let falta = Math.round(raw.reduce((a, b) => a + b, 0)) - base.reduce((a, b) => a + b, 0);
            raw.map((v, i) => [v - base[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => {
                if (falta > 0) {
                    base[i] += 1;
                    falta -= 1;
                }
            });
            return base;
        };
        const CEL = 10;
        const SEP = 3;
        const LADO = 10 * CEL + 9 * SEP;
        const waffle = (segs, total) => {
            const k = total ? reparto(segs, total) : segs.map(() => 0);
            const seq = [];
            segs.forEach((s, i) => {
                for (let j = 0; j < k[i]; j += 1) {
                    seq.push(s);
                }
            });
            let r = "";
            for (let i = 0; i < 100; i += 1) {
                const x = (i % 10) * (CEL + SEP);
                const y = (9 - Math.floor(i / 10)) * (CEL + SEP);
                r += `<rect x="${x}" y="${y}" width="${CEL}" height="${CEL}" rx="2" fill="${seq[i] ? seq[i][2] : C.track}"/>`;
            }
            return `<svg class="tpc-waffle" width="${LADO}" height="${LADO}" viewBox="0 0 ${LADO} ${LADO}" role="img" aria-label="${
                segs.map((s) => `${s[0]}: ${fmt(s[1])}`).join(", ")}">${r}</svg>`;
        };
        const ley = (segs, total) => `<ul class="tpc-ley">${segs.map((s) => `<li><i style="background:${s[2]}"></i><span>${s[0]}</span><b>${
            fmt(s[1])}</b><em>${pct(s[1], total, s[1] && 100 * s[1] / total < 1 ? 2 : 0)}</em></li>`).join("")}</ul>`;
        const card = (valor, titulo, segs, total, pie) => `<div class="tpc-kpi"><div class="tpc-kpi-cabeza"><b>${valor}</b><span>${
            titulo}</span></div><div class="tpc-kpi-fila">${waffle(segs, total)}${ley(segs, total)}</div><div class="tpc-kpi-pie">${pie}</div></div>`;
        const sPad = [["Inscriptos al curso", ins, C.teal], ["No inscriptos", padron - ins, C.track]];
        const sIns = ESTADOS.map((e) => [e, est(e), colEstado(e)]);
        const sRin = [["Aprobaron", apr, C.teal], ["No aprobaron", est("Rindió y no aprobó"), C.rojo]];
        document.getElementById("tpc-kpis").innerHTML = card(fmt(padron), "Titulares", sPad, padron,
            `Cada cuadradito es el 1 % del padrón · se inscribió ${ins && padron ? `1 de cada ${fmt(Math.round(padron / ins))}` : "nadie"}`)
            + card(fmt(ins), "Inscriptos", sIns, ins,
                `Cada cuadradito es el 1 % de los inscriptos · edad promedio ${edadN ? dec(edadS / edadN) : "—"} años`)
            + card(fmt(rind), "Rindieron", sRin, rind,
                `${pct(rind, ins, 0)} de los inscriptos rindió · ${fmt(est("Certificado"))} certificados emitidos`);
    }

    /* ---------- Tarjetas de seguimiento ---------- */
    function drawKpis2() {
        const corte = (T.fecha_carga || "").slice(0, 10);
        const menos = (dias) => {
            const d = new Date(`${corte}T12:00:00`);
            d.setDate(d.getDate() - dias);
            return d.toISOString().slice(0, 10);
        };
        const evol = D.evol.filter(enAlcance);
        const ult = suma(evol, (r) => r[3] > menos(7), 4);
        const ant = suma(evol, (r) => r[3] > menos(14) && r[3] <= menos(7), 4);
        const varTxt = ant ? `${ult >= ant ? "▲ +" : "▼ "}${dec(100 * (ult - ant) / ant, 0)} %` : "";
        const trab = D.trab.filter(enAlcance);
        const sinRendir = suma(trab, () => true, 4);
        const t7 = suma(trab, (r) => r[3] !== "hasta 7", 4);
        const t30 = suma(trab, (r) => r[3] === "más de 30", 4);
        const tiempo = D.tiempo.filter(enAlcance);
        const apr = suma(tiempo, () => true, 4);
        const h1 = suma(tiempo, (r) => r[3] === "menos de 1 h", 4);
        const h24 = h1 + suma(tiempo, (r) => r[3] === "1 a 24 h", 4);
        const card = (icono, valor, titulo, detalle, color) => `<div class="tpc-kpi tpc-kpi-chica"><div class="tpc-kpi-chica-ico" style="color:${
            color}"><i class="bi ${icono}"></i></div><div><div class="tpc-kpi-cabeza"><b>${valor}</b><span>${titulo}</span></div><div class="tpc-kpi-pie">${
            detalle}</div></div></div>`;
        document.getElementById("tpc-kpis2").innerHTML = card("bi-calendar-week", fmt(ult), "inscriptos esta semana",
            `Últimos 7 días · semana anterior: ${fmt(ant)}${varTxt ? ` <b style="color:${ult >= ant ? C.teal : C.rojo}">${varTxt}</b>` : ""}`, C.azul)
            + card("bi-hourglass-split", fmt(t7), "trabados",
                `Se inscribieron, no rindieron y no entran hace más de 7 días (de ${fmt(sinRendir)} sin rendir) · ${fmt(t30)} hace más de 30`, C.ambar)
            + card("bi-lightning-charge", apr ? pct(h1, apr, 0) : "—", "aprobó en menos de 1 hora",
                `Desde que entró al curso hasta que aprobó · ${apr ? pct(h24, apr, 0) : "—"} en el mismo día`, C.teal);
    }

    /* ---------- Inscriptos y aprobados en el tiempo ---------- */
    function drawEvolucion() {
        const rows = D.evol.filter(enAlcance);
        const porDia = new Map();
        rows.forEach((r) => {
            const x = porDia.get(r[3]) || [0, 0];
            x[0] += r[4];
            x[1] += r[5];
            porDia.set(r[3], x);
        });
        const todos = D.evol.map((r) => r[3]).sort();
        const dias = [];
        if (todos.length) {
            for (let d = new Date(`${todos[0]}T12:00:00`); d.toISOString().slice(0, 10) <= todos[todos.length - 1]; d.setDate(d.getDate() + 1)) {
                dias.push(d.toISOString().slice(0, 10));
            }
        }
        let ai = 0;
        let aa = 0;
        const nIns = dias.map((d) => (porDia.get(d) || [0, 0])[0]);
        const nApr = dias.map((d) => (porDia.get(d) || [0, 0])[1]);
        const acIns = nIns.map((v) => { ai += v; return ai; });
        const acApr = nApr.map((v) => { aa += v; return aa; });
        const lab = dias.map((d) => `${d.slice(8, 10)}/${d.slice(5, 7)}`);
        leyenda("ley-evolucion", [["Inscriptos", C.azul], ["Aprobados", C.teal]]);
        alto("evolucion", 280);
        const linea = (label, data, color) => ({
            type: "line", label, data, borderColor: color, backgroundColor: color, borderWidth: 2.5,
            pointRadius: 0, pointHoverRadius: 4, tension: 0.15,
        });
        dibujar("evolucion", {
            type: "line",
            data: { labels: lab, datasets: [linea("Inscriptos", acIns, C.azul), linea("Aprobados", acApr, C.teal)] },
            options: {
                interaction: { mode: "index", intersect: false },
                layout: { padding: { right: 60 } },
                scales: {
                    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 10, maxRotation: 0 } },
                    y: { beginAtZero: true, grid: { color: C.grilla }, border: { display: false }, ticks: { callback: (v) => fmt(v), maxTicksLimit: 5 } },
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: (c) => fechaLarga(dias[c[0].dataIndex]),
                            label: (c) => `${c.dataset.label}: ${fmt(c.raw)} (+${fmt((c.datasetIndex ? nApr : nIns)[c.dataIndex])} ese día)`,
                        },
                    },
                },
            },
            plugins: [{
                id: "tpcFinLinea",   // valor final a la derecha de cada línea
                afterDatasetsDraw(ch) {
                    const { ctx } = ch;
                    ctx.save();
                    ctx.font = "500 12px Roboto, sans-serif";
                    ctx.textBaseline = "middle";
                    ch.data.datasets.forEach((ds, i) => {
                        const p = ch.getDatasetMeta(i).data.at(-1);
                        if (p) {
                            ctx.fillStyle = ds.borderColor;
                            ctx.fillText(fmt(ds.data.at(-1)), p.x + 6, p.y);
                        }
                    });
                    ctx.restore();
                },
            }],
        }, {
            head: ["Día", "Inscriptos ese día", "Inscriptos acumulados", "Aprobados ese día", "Aprobados acumulados", "% aprobados"],
            rows: dias.map((d, i) => [fechaLarga(d), nIns[i], acIns[i], nApr[i], acApr[i], pct(acApr[i], acIns[i], 0)]).reverse(),
        });
    }

    /* ---------- Inscripción y resultados por jurisdicción ---------- */
    function porProvincia() {
        const t = {};
        D.cubo.filter(enLinea).forEach((r) => {
            if (!t[r[0]]) {
                t[r[0]] = { c: String(r[0]), p: nomProv(r[0]), pad: 0, ins: 0, rin: 0, apr: 0, des: 0, sin: 0 };
            }
            const x = t[r[0]];
            x.pad += r[5];
            if (r[2] === "No inscripto") {
                return;
            }
            x.ins += r[5];
            if (RINDIERON.includes(r[2])) { x.rin += r[5]; }
            if (APROBARON.includes(r[2])) { x.apr += r[5]; }
            if (r[2] === "Rindió y no aprobó") { x.des += r[5]; }
            if (r[2] === "Inscripto sin rendir") { x.sin += r[5]; }
        });
        return Object.values(t);
    }
    function drawJurisdiccion() {
        // El servidor ya mandó solo las provincias del alcance del usuario. Con una elegida, las demás se atenúan.
        const r = porProvincia().sort((a, b) => b.ins / b.pad - a.ins / a.pad || b.ins - a.ins);
        const maxPct = Math.max(...r.map((x) => x.ins / x.pad), 0);
        const series = [["Aprobaron", "apr", C.teal, "#fff"], ["No aprobaron", "des", C.rojo, "#fff"], ["Sin rendir", "sin", C.ambar, C.sobreClaro]];
        leyenda("ley-jurisdiccion", [["% de titulares inscriptos", C.azul], ...series.map((s) => [s[0], s[2]])]);
        const pctTxt = (x) => {
            const v = 100 * x.ins / x.pad;
            return x.ins ? `${dec(v, v < 1 ? 2 : 1)} %` : "0 %";
        };
        const filas = r.map((x) => {
            const ancho = x.ins && maxPct ? Math.max(1.5, 100 * (x.ins / x.pad) / maxPct) : 0;   // mínimo visible
            const mix = x.ins ? `<div class="tpc-mix">${series.map(([nombre, k, c, t]) => {
                const w = 100 * x[k] / x.ins;
                return w ? `<i style="width:${w}%;background:${c};color:${t}" title="${nombre}: ${fmt(x[k])} (${dec(w)} %)">${w >= 12 ? `${dec(w, 0)} %` : ""}</i>` : "";
            }).join("")}</div>` : '<span class="tpc-jur-vacio">sin inscriptos</span>';
            const clase = state.prov && x.c !== state.prov ? ' class="tpc-jur-atenuada"' : "";
            return `<tr${clase}><td>${x.p}</td><td>${fmt(x.pad)}</td><td>${fmt(x.ins)}</td>`
                + `<td class="tpc-jur-barra"><div class="tpc-jur-pct"><span><i style="width:${ancho}%;background:${C.azul}"></i></span><b>${pctTxt(x)}</b></div></td>`
                + `<td class="tpc-jur-barra">${mix}</td></tr>`;
        }).join("");
        document.getElementById("tbl-jurisdiccion").innerHTML = "<thead><tr><th>Jurisdicción</th><th>Titulares</th><th>Inscriptos</th>"
            + `<th>% inscripto</th><th>Resultado de los inscriptos</th></tr></thead><tbody>${filas}</tbody>`;
        tables.jurisdiccion = {
            head: ["Jurisdicción", "Titulares", "Inscriptos", "% inscripto", "Rindieron", "% presentación", "Aprobados", "% aprobados", "No aprobaron", "Sin rendir"],
            rows: [...r].sort((a, b) => b.ins - a.ins).map((x) => [x.p, x.pad, x.ins, pct(x.ins, x.pad, 2), x.rin, pct(x.rin, x.ins),
                x.apr, pct(x.apr, x.rin), x.des, x.sin]),
        };
        refrescarTabla("jurisdiccion");
    }

    /* ---------- Edad y género ---------- */
    function drawEdad() {
        const cubo = D.cubo.filter(enAlcance).filter((r) => r[2] !== "No inscripto");
        const G = GENEROS.map(([g]) => RANGOS.map((ra) => suma(cubo, (r) => r[3] === g && r[4] === ra, 5)));
        const TOT = RANGOS.map((ra, i) => G.reduce((s, x) => s + x[i], 0));
        leyenda("ley-edad", GENEROS.map(([g, n]) => [n, colGenero(g)]));
        alto("edad", RANGOS.length * 36 + 20);
        dibujar("edad", {
            type: "bar",
            data: {
                labels: RANGOS.map((ra, i) => `${ra} años · ${fmt(TOT[i])}`),
                datasets: GENEROS.map(([g, n], k) => barra(n, G[k], colGenero(g), { stack: "s" })),
            },
            options: {
                indexAxis: "y",
                scales: { x: ejeOculto(Math.max(1, ...TOT), { stacked: true }), y: Object.assign(ejeCat(), { stacked: true }) },
                plugins: {
                    tpcEtiquetas: { formato: (x) => (x ? fmt(x) : ""), color: (i) => (i === 1 ? C.sobreAzul : "#fff") },
                    tooltip: {
                        callbacks: {
                            title: (c) => `${RANGOS[c[0].dataIndex]} años · ${fmt(TOT[c[0].dataIndex])} inscriptos`,
                            label: (c) => `${c.dataset.label}: ${fmt(c.raw)} · ${pct(c.raw, TOT[c.dataIndex], 0)}`,
                        },
                    },
                },
            },
        }, {
            head: ["Edad", ...GENEROS.map((g) => g[1]), "Total"],
            rows: RANGOS.map((ra, i) => [`${ra} años`, ...G.map((x) => x[i]), TOT[i]]),
        });
    }
    // Tasa de inscripción = inscriptos / titulares de cada edad y género. El género X va solo en la tabla.
    function drawPerfil() {
        const cubo = D.cubo.filter(enAlcance);
        const tit = (g, ra) => suma(cubo, (r) => (!g || r[3] === g) && r[4] === ra, 5);
        const ins = (g, ra) => suma(cubo, (r) => (!g || r[3] === g) && r[4] === ra && r[2] !== "No inscripto", 5);
        const tasa = (g, ra) => {
            const t = tit(g, ra);
            return t ? 100 * ins(g, ra) / t : 0;
        };
        const G = [["F", "Mujeres"], ["M", "Varones"]];
        const V = G.map(([g]) => RANGOS.map((ra) => tasa(g, ra)));
        const tot = RANGOS.map((ra) => tasa("", ra));
        const txt = (x) => (x ? `${dec(x, x < 1 ? 2 : 1)} %` : "");
        leyenda("ley-perfil", G.map(([g, n]) => [n, colGenero(g)]));
        alto("perfil", RANGOS.length * 44 + 20);
        dibujar("perfil", {
            type: "bar",
            data: {
                labels: RANGOS.map((ra, i) => `${ra} años · ${txt(tot[i]) || "0 %"}`),
                datasets: G.map(([g, n], k) => barra(n, V[k], colGenero(g), { maxBarThickness: 16 })),
            },
            options: {
                indexAxis: "y",
                layout: { padding: { right: 50 } },
                scales: { x: ejeOculto(Math.max(0.01, ...V.flat())), y: ejeCat() },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: (c) => `${RANGOS[c[0].dataIndex]} años · total ${txt(tot[c[0].dataIndex]) || "0 %"}`,
                            label: (c) => {
                                const g = G[c.datasetIndex][0];
                                const ra = RANGOS[c.dataIndex];
                                return `${c.dataset.label}: ${txt(c.raw) || "0 %"} (${fmt(ins(g, ra))} de ${fmt(tit(g, ra))})`;
                            },
                        },
                    },
                },
            },
            plugins: [{
                id: "tpcTasaFuera",   // la tasa a la derecha de cada barra
                afterDatasetsDraw(ch) {
                    const { ctx } = ch;
                    ctx.save();
                    ctx.font = "11.5px Roboto, sans-serif";
                    ctx.fillStyle = C.gris2;
                    ctx.textBaseline = "middle";
                    ch.data.datasets.forEach((ds, i) => ch.getDatasetMeta(i).data.forEach((elem, j) => {
                        const t = txt(V[i][j]);
                        if (t) {
                            ctx.fillText(t, elem.x + 5, elem.y);
                        }
                    }));
                    ctx.restore();
                },
            }],
        }, {
            head: ["Edad", "Titulares", "Inscriptos", "Tasa", "Tasa mujeres", "Tasa varones", "Tasa X"],
            rows: RANGOS.map((ra) => [`${ra} años`, tit("", ra), ins("", ra), pct(ins("", ra), tit("", ra), 2),
                pct(ins("F", ra), tit("F", ra), 2), pct(ins("M", ra), tit("M", ra), 2), pct(ins("X", ra), tit("X", ra), 2)]),
        });
    }

    /* ---------- Encabezado: alcance, línea, borrar filtros, fecha del dato ---------- */
    const fProv = document.getElementById("tpc-filtro-provincia");
    const fLinea = document.getElementById("tpc-filtro-linea");
    const btnBorrar = document.getElementById("tpc-borrar-filtros");

    function drawEncabezado() {
        const candado = PROVINCIAL ? '<i class="bi bi-lock-fill" aria-hidden="true"></i> ' : "";
        let alcanceTxt = "Todas las jurisdicciones";
        if (state.prov) {
            alcanceTxt = nomProv(state.prov);
        } else if (PROVINCIAL) {
            alcanceTxt = IDS.map(nomProv).join(" + ");
        }
        document.getElementById("tpc-chip-alcance").innerHTML = candado + alcanceTxt;
        document.getElementById("tpc-chip-linea").innerHTML = `<i class="bi bi-funnel-fill" aria-hidden="true"></i> Línea: ${esc(state.linea || "todas")}`;
        document.getElementById("tpc-filtro-linea-caja").classList.toggle("tpc-filtro-activo", Boolean(state.linea));
        btnBorrar.disabled = state.prov === provDefecto() && state.linea === LINEA_DEF;
    }
    function marcarActualizacion() {
        const chip = document.getElementById("tpc-chip-actualizado");
        if (!T.fecha_carga) {
            chip.textContent = "Sin datos cargados";
            return;
        }
        const carga = new Date(`${T.fecha_carga.replace(" ", "T")}:00`);
        const fechaTxt = `${fechaLarga(T.fecha_carga.slice(0, 10))} ${T.fecha_carga.slice(11)}`;
        const horas = (new Date() - carga) / 3600000;
        if (horas > 24) {   // la carga diaria dejó de correr
            const dias = Math.floor(horas / 24);
            chip.classList.add("tpc-chip-viejo");
            chip.innerHTML = `<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i> Actualizado hace ${dias} ${dias === 1 ? "día" : "días"} (${fechaTxt})`;
            chip.title = "Los datos no se actualizan desde esa fecha";
        } else {
            chip.textContent = `Actualizado: ${fechaTxt}`;
            chip.title = "Fecha y hora de la última carga de datos";
        }
    }

    function drawAll() {
        drawEncabezado();
        drawKpis();
        drawKpis2();
        drawEvolucion();
        drawJurisdiccion();
        drawEdad();
        drawPerfil();
    }

    /* ---------- Inicio ---------- */
    if (T.alcance === "sin_alcance" || T.sin_datos) {
        const aviso = T.alcance === "sin_alcance" ? ".tpc-sin-jurisdiccion" : ".tpc-sin-datos";
        raiz.querySelector(aviso).classList.remove("tpc-oculto");
        raiz.querySelectorAll(".tpc-con-datos").forEach((el) => el.classList.add("tpc-oculto"));
        return;
    }
    let primera = '<option value="">Todas las jurisdicciones</option>';
    if (PROVINCIAL) {
        primera = IDS.length > 1 ? `<option value="">Mis jurisdicciones (${IDS.map(nomProv).join(", ")})</option>` : "";
    }
    fProv.innerHTML = primera + IDS.map((id) => `<option value="${esc(id)}">${nomProv(id)}</option>`).join("");
    fProv.value = state.prov;
    fProv.disabled = PROVINCIAL && IDS.length === 1;
    if (fProv.disabled) {
        fProv.title = "Tu usuario solo ve esta jurisdicción";
    }
    fLinea.innerHTML = `<option value="">Todas las líneas</option>${LINEAS.map((l) => `<option${l === LINEA_DEF ? " selected" : ""}>${l}</option>`).join("")}`;
    fProv.addEventListener("change", () => { state.prov = fProv.value; drawAll(); });
    fLinea.addEventListener("change", () => { state.linea = fLinea.value; drawAll(); });
    btnBorrar.addEventListener("click", () => {   // como "Restablecer filtros" del Power BI
        state.prov = provDefecto();
        state.linea = LINEA_DEF;
        fProv.value = state.prov;
        fLinea.value = LINEA_DEF;
        drawAll();
    });
    raiz.querySelectorAll(".tpc-btn-tabla").forEach((b) => b.addEventListener("click", () => {
        const sec = b.closest(".tpc-seccion");
        const wrap = sec.querySelector(".tpc-tblwrap");
        const ch = sec.querySelector(".tpc-chart");
        const ver = wrap.classList.contains("tpc-oculto");
        wrap.classList.toggle("tpc-oculto", !ver);
        if (ch) {
            ch.classList.toggle("tpc-oculto", ver);
        }
        b.textContent = ver ? "Gráfico" : "Tabla";
        if (ver) {
            refrescarTabla(sec.dataset.id);
        }
    }));
    marcarActualizacion();
    drawAll();
}());
