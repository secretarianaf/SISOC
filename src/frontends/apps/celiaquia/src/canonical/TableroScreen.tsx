import { useMemo, useState, type ReactNode } from "react";
import { Alert, Box, Button, Chip, FormHelperText, Paper, Stack, Typography } from "@mui/material";
import { internal } from "./transport";
import { Loading, Messages, useProjection, type Message } from "./PagosScreens";

/*
 * Celiaquía follow-up dashboard. Same data and rules as the native page
 * (`tablero.html` + `tablero_celiaquia.js`): the server sends aggregated counts
 * only, and the province / expediente filters run here over that data.
 * Charts are drawn as accessible CSS bars; every chart has its data table.
 */

const CAMPOS = ["leg", "pend", "apr", "rech", "sub", "match", "nomatch", "sincruce", "tit", "susp", "fuera"] as const;
type Counts = Record<(typeof CAMPOS)[number], number>;
type ProvRow = Counts & { p: string; cupo: number; exp: number; expProc: number; per: number };
type ExpRow = Counts & { id: number; n: string; est: string; d: number; p: string };
type ExpScope = ExpRow & { provs: string[]; porResolver: number };
type PorProvincia = Record<string, Record<string, number>>;
type Datos = {
  provincias: ProvRow[]; expedientes: ExpRow[]; tramos: string[];
  piramide: Record<string, { F: number[]; M: number[] }>;
  rechazo: PorProvincia; subsanacion: PorProvincia; errores: PorProvincia;
};
type TableroData = { version: number; datos: Datos; url_expediente: string; messages: Message[] };
type Tabla = { head: string[]; rows: (string | number)[][] };

const EST: Record<string, string> = {
  CRUCE_FINALIZADO: "Cruce finalizado", CONFIRMACION_DE_ENVIO: "Confirmación de envío", ASIGNADO: "Asignado",
  EN_ESPERA: "En espera", CREADO: "Creado", PROCESADO: "Procesado", RECEPCIONADO: "Recepcionado", PROCESO_DE_CRUCE: "Proceso de cruce",
};
const C = { teal: "#3b8681", ambar: "#e7a13a", rojo: "#e5534b", gris: "#8a94a8", azul: "#5f7fc0", track: "#dde2ea", gris2: "#6b7487" };
const ESCALA = ["#2a3b5e", "#1f4b48", "#2f6b67", "#3b8681", "#6fb3ac"];

const nf = new Intl.NumberFormat("es-AR");
const fmt = (n: number) => nf.format(n);
const pct = (a: number, b: number, d = 1) => (b ? `${(100 * a / b).toFixed(d).replace(".", ",")} %` : "—");
const sum = (rows: Counts[], k: keyof Counts | "cupo" | "exp" | "expProc") => rows.reduce((s, r) => s + ((r as Record<string, number>)[k] ?? 0), 0);
const estado = (est: string) => EST[est] || est;
const srOnly = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" } as const;

function sumarCat(P: PorProvincia, rows: ProvRow[]): [string, number][] {
  const t: Record<string, number> = {};
  rows.forEach((r) => Object.entries(P[r.p] || {}).forEach(([k, v]) => { t[k] = (t[k] || 0) + v; }));
  return Object.entries(t).sort((a, b) => b[1] - a[1]);
}

/** Expedientes of the selected province, merging rows of the same id (citizens of two provinces). */
function expedientesEnAlcance(exps: ExpRow[], prov: string): ExpScope[] {
  const m = new Map<number, ExpScope>();
  exps.filter((e) => !prov || e.p === prov).forEach((e) => {
    const x = m.get(e.id);
    if (!x) { m.set(e.id, { ...e, provs: [e.p], porResolver: 0 }); return; }
    CAMPOS.forEach((k) => { x[k] += e[k]; });
    x.provs.push(e.p);
  });
  return [...m.values()].map((x) => ({ ...x, p: x.provs.join(" + "), porResolver: x.pend + x.sub }));
}

/* ---------- Building blocks ---------- */

function Leyenda({ items }: { items: [string, string, boolean?][] }) {
  return <Box component="ul" aria-hidden="true" sx={{ display: "flex", flexWrap: "wrap", gap: 2, listStyle: "none", p: 0, m: 0, mb: 1, fontSize: 13 }}>
    {items.map(([n, c, outline]) => <li key={n} style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <i style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, ...(outline ? { border: `2px solid ${c}` } : { background: c }) }} />{n}
    </li>)}
  </Box>;
}

function DataTable({ tabla, label }: { tabla: Tabla; label: string }) {
  return <Box sx={{ overflowX: "auto" }}>
    <Box component="table" aria-label={label} sx={{ width: "100%", borderCollapse: "collapse", fontSize: 14, "& th, & td": { borderBottom: "1px solid", borderColor: "divider", p: 0.75, textAlign: "left" } }}>
      <thead><tr>{tabla.head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
      <tbody>{tabla.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{typeof c === "number" ? fmt(c) : c}</td>)}</tr>)}</tbody>
    </Box>
  </Box>;
}

type Segment = { name: string; value: number; color: string; text?: string; detail?: string };
type BarRow = { label: string; segments: Segment[] };

/** Horizontal (stacked) bars; the value is written inside when it fits, as in the native chart. */
function Barras({ rows, max }: { rows: BarRow[]; max: number }) {
  return <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, display: "grid", gap: 0.75 }}>
    {rows.map((row) => {
      const resumen = row.segments.map((s) => `${s.name}: ${s.detail ?? fmt(s.value)}`).join(", ");
      return <Box component="li" key={row.label} sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "minmax(8rem, 30%) 1fr" }, gap: { xs: 0.25, sm: 1 }, alignItems: "center", fontSize: 13 }}>
        <span>{row.label}</span>
        <Box role="img" aria-label={`${row.label}. ${resumen}`} title={resumen} sx={{ display: "flex", height: 22, bgcolor: "action.hover", borderRadius: 0.75, overflow: "hidden" }}>
          {row.segments.map((s) => s.value > 0 && <Box key={s.name} sx={{ width: `${(100 * s.value) / max}%`, bgcolor: s.color, color: "#fff", fontSize: 11, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", whiteSpace: "nowrap" }}>{s.text ?? ""}</Box>)}
        </Box>
      </Box>;
    })}
  </Box>;
}

function Seccion({ titulo, nota, tabla, children, pie }: { titulo: string; nota?: string; tabla?: Tabla; children: ReactNode; pie?: ReactNode }) {
  const [verTabla, setVerTabla] = useState(false);
  return <Paper component="section" sx={{ p: 2, minWidth: 0 }}>
    <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
      <Typography variant="subtitle1" component="h2" sx={{ fontWeight: 600 }}>
        {titulo}{nota && <Typography component="span" variant="body2" color="text.secondary"> {nota}</Typography>}
      </Typography>
      {tabla && <Button size="small" variant="outlined" onClick={() => setVerTabla(!verTabla)}>{verTabla ? "Gráfico" : "Tabla"}</Button>}
    </Stack>
    {tabla && verTabla ? <DataTable tabla={tabla} label={titulo} /> : children}
    {pie}
  </Paper>;
}

const Nota = ({ children }: { children: string }) => (children ? <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{children}</Typography> : null);

/* ---------- KPI cards with a 10 x 10 waffle ---------- */

type Seg = [string, number, string, boolean?];

/** Largest remainder: the cells add up to what they represent. */
function reparto(segs: Seg[], total: number, celdas: number) {
  const raw = segs.map((s) => (celdas * s[1]) / total);
  const base = raw.map(Math.floor);
  let falta = Math.round((celdas * segs.reduce((a, s) => a + s[1], 0)) / total) - base.reduce((a, b) => a + b, 0);
  raw.map((v, i) => [v - base[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => {
    if (falta > 0) { base[i] += 1; falta -= 1; }
  });
  return base;
}

function Waffle({ segs, total, celdas = 100 }: { segs: Seg[]; total: number; celdas?: number }) {
  const CEL = 10, SEP = 3, LADO = 10 * CEL + 9 * SEP;
  const n = total ? reparto(segs, total, celdas) : segs.map(() => 0);
  const seq: Seg[] = [];
  segs.forEach((s, i) => { for (let j = 0; j < n[i]; j += 1) seq.push(s); });
  const rects = Array.from({ length: 100 }, (_, i) => {
    const x = (i % 10) * (CEL + SEP);
    const y = (9 - Math.floor(i / 10)) * (CEL + SEP);
    const s = seq[i];
    if (!s) return <rect key={i} x={x} y={y} width={CEL} height={CEL} rx={2} fill={C.track} />;
    if (s[3]) return <rect key={i} x={x + 1} y={y + 1} width={CEL - 2} height={CEL - 2} rx={1.5} fill="none" stroke={s[2]} strokeWidth={2} />;
    return <rect key={i} x={x} y={y} width={CEL} height={CEL} rx={2} fill={s[2]} />;
  });
  return <svg width={LADO} height={LADO} viewBox={`0 0 ${LADO} ${LADO}`} role="img" aria-label={segs.map((s) => `${s[0]}: ${fmt(s[1])}`).join(", ")} style={{ flexShrink: 0 }}>{rects}</svg>;
}

function Kpi({ valor, titulo, segs, total, waffle, pie }: { valor: string; titulo: string; segs: Seg[]; total: number; waffle: ReactNode; pie: string }) {
  return <Paper sx={{ p: 2 }}>
    <Stack direction="row" spacing={1} sx={{ alignItems: "baseline", mb: 1 }}>
      <Typography component="b" variant="h5" sx={{ fontWeight: 700 }}>{valor}</Typography>
      <Typography component="span">{titulo}</Typography>
    </Stack>
    <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap", gap: 1 }}>
      {waffle}
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, fontSize: 13, display: "grid", gap: 0.5 }}>
        {segs.map((s) => <li key={s[0]} style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <i aria-hidden="true" style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, ...(s[3] ? { border: `2px solid ${s[2]}` } : { background: s[2] }) }} />
          <span>{s[0]}</span><b>{fmt(s[1])}</b><em>{pct(s[1], total, 0)}</em>
        </li>)}
      </Box>
    </Stack>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{pie}</Typography>
  </Paper>;
}

function Kpis({ rows }: { rows: Counts[] }) {
  const g = (k: Parameters<typeof sum>[1]) => sum(rows, k);
  const leg = g("leg"), apr = g("apr"), tit = g("tit"), exp = g("exp"), expProc = g("expProc"), cupo = g("cupo"), fuera = g("fuera");
  const sExp: Seg[] = [["Cruce finalizado", exp - expProc, C.azul], ["En proceso", expProc, C.gris]];
  const sPer: Seg[] = [["Aprobadas", apr, C.teal], ["A subsanar", g("sub"), C.ambar], ["Rechazadas", g("rech"), C.rojo], ["Pendientes", g("pend"), C.gris]];
  const sTit: Seg[] = [["Titulares", tit, C.azul], ["No llegan", apr - tit, C.teal, true]];
  return <Box component="section" aria-label="Cifras principales" sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 2 }}>
    <Kpi valor={fmt(exp)} titulo="Expedientes" segs={sExp} total={exp} waffle={<Waffle segs={sExp} total={1} celdas={1} />}
      pie={`Cada cuadradito es un expediente · ${exp ? Math.round(leg / exp) : 0} personas por expediente en promedio`} />
    <Kpi valor={fmt(leg)} titulo="Personas cargadas" segs={sPer} total={leg} waffle={<Waffle segs={sPer} total={leg} />}
      pie="Cada cuadradito es el 1 % · estado de la revisión técnica · sin responsables" />
    <Kpi valor={fmt(tit)} titulo="Titulares" segs={sTit} total={leg} waffle={<Waffle segs={sTit} total={leg} />}
      pie={`No llegan: ${fmt(apr - tit)} aprobadas que no son titulares (${fmt(g("nomatch"))} sin coincidencia SINTyS · ${fmt(g("sincruce"))} sin cruzar${fuera ? ` · ${fmt(fuera)} fuera de cupo` : ""}) · cupo usado ${pct(tit, cupo, 0)}`} />
  </Box>;
}

/* ---------- Sections ---------- */

function Cupo({ rows }: { rows: ProvRow[] }) {
  const r = [...rows].sort((a, b) => b.tit - a.tit || b.cupo - a.cupo);
  const max = Math.max(1, ...r.map((x) => Math.max(x.cupo, x.tit)));
  return <Seccion titulo="Cupo usado por provincia" nota="titulares sobre cupo asignado"
    tabla={{ head: ["Provincia", "Cupo asignado", "Titulares", "Disponible", "% usado"], rows: r.map((x) => [x.p, x.cupo, x.tit, x.cupo - x.tit, pct(x.tit, x.cupo)]) }}>
    <Leyenda items={[["Usado (titulares)", C.teal], ["Disponible", C.track]]} />
    <Barras max={max} rows={r.map((x) => ({ label: x.p, segments: [
      { name: "Usado", value: x.tit, color: C.teal, text: x.tit && x.cupo ? pct(x.tit, x.cupo, 0) : "", detail: `${fmt(x.tit)} · ${pct(x.tit, x.cupo)} del cupo` },
      { name: "Disponible", value: Math.max(0, x.cupo - x.tit), color: C.track },
    ] }))} />
  </Seccion>;
}

function Piramide({ rows, datos }: { rows: ProvRow[]; datos: Datos }) {
  const P = datos.piramide, T = datos.tramos;
  const F = T.map((_, i) => rows.reduce((s, r) => s + (P[r.p] ? P[r.p].F[i] : 0), 0));
  const M = T.map((_, i) => rows.reduce((s, r) => s + (P[r.p] ? P[r.p].M[i] : 0), 0));
  const TOT = F.map((v, i) => v + M[i]);
  return <Seccion titulo="Titulares por edad y género" nota="sin responsables"
    tabla={{ head: ["Tramo", "Mujeres", "Varones", "Total"], rows: T.map((t, i) => [t, F[i], M[i], TOT[i]]) }}>
    <Leyenda items={[["Mujeres", C.teal], ["Varones", C.azul]]} />
    <Barras max={Math.max(1, ...TOT)} rows={T.map((t, i) => ({ label: `${t} · ${fmt(TOT[i])}`, segments: [
      { name: "Mujeres", value: F[i], color: C.teal, text: F[i] ? fmt(F[i]) : "" },
      { name: "Varones", value: M[i], color: C.azul, text: M[i] ? fmt(M[i]) : "" },
    ] }))} />
  </Seccion>;
}

const detalle = (quedan: [string, number][]) => quedan.filter((x) => x[1]).map(([n, v]) => `${fmt(v)} ${n}`).join(" · ");

function Embudo({ rows }: { rows: Counts[] }) {
  const g = (k: keyof Counts) => sum(rows, k);
  const st = [
    { n: "Cargados", sigue: g("leg"), quedan: [] as [string, number][] },
    { n: "Revisión técnica", sigue: g("apr"), quedan: [["a subsanar", g("sub")], ["rechazadas", g("rech")], ["pendientes de revisar", g("pend")]] as [string, number][] },
    { n: "Cruce SINTyS", sigue: g("match"), quedan: [["sin coincidencia", g("nomatch")], ["todavía sin cruzar", g("sincruce")]] as [string, number][] },
    { n: "Cupo provincial", sigue: g("tit"), quedan: [["fuera de cupo", g("fuera")], ["suspendidos", g("susp")]] as [string, number][] },
  ].map((s) => ({ ...s, q: s.quedan.reduce((a, x) => a + x[1], 0) }));
  const base = st[0].sigue;
  return <Seccion titulo="Circuito del beneficiario" nota="siguen y se quedan en cada paso"
    tabla={{ head: ["Paso", "Siguen", "% de cargados", "Se quedan", "Detalle"], rows: st.map((s) => [s.n, s.sigue, pct(s.sigue, base), s.q, detalle(s.quedan) || "—"]) }}>
    <Leyenda items={[["Siguen", C.azul], ["Se quedan en este paso", C.gris]]} />
    <Barras max={Math.max(1, base)} rows={st.map((s, i) => ({ label: s.n, segments: [
      { name: "Siguen", value: s.sigue, color: C.azul, text: s.sigue ? (i === 0 ? `${fmt(s.sigue)} · ${pct(s.sigue, base, 0)}` : fmt(s.sigue)) : "", detail: `${fmt(s.sigue)} · ${pct(s.sigue, base, 0)} de los cargados` },
      { name: "Se quedan", value: s.q, color: C.gris, text: s.q ? fmt(s.q) : "", detail: detalle(s.quedan) || "—" },
    ] }))} />
    <Box component="ul" sx={{ fontSize: 13, mt: 1, mb: 0, pl: 2.5 }}>
      {st.slice(1).map((s) => <li key={s.n}><strong>{s.n}:</strong> se quedan {fmt(s.q)}{s.q ? ` (${detalle(s.quedan)})` : ""}</li>)}
    </Box>
  </Seccion>;
}

function Conversion({ rows }: { rows: ProvRow[] }) {
  const r = [...rows].sort((a, b) => b.leg - a.leg);
  const etapas: [string, (x: ProvRow) => [number, number]][] = [
    ["Carga → aprobado", (x) => [x.apr, x.leg]],
    ["Aprobado → validado SINTyS", (x) => [x.match, x.apr]],
    ["Validado SINTyS → titular", (x) => [x.tit, x.match]],
  ];
  const celda = ([a, b]: [number, number], key: number) => {
    if (!b) return <td key={key} style={{ background: C.track, color: "#555", textAlign: "center" }}>—</td>;
    const v = Math.round((100 * a) / b);
    const i = Math.min(4, Math.floor(v / 20));
    return <td key={key} title={`${fmt(a)} de ${fmt(b)}`} style={{ background: ESCALA[i], color: i === 4 ? "#0b0b0b" : "#fff", textAlign: "center" }}>{v} %</td>;
  };
  return <Seccion titulo="Paso entre etapas" nota="% que pasa a la siguiente"
    tabla={{ head: ["Provincia", ...etapas.map((e) => e[0])], rows: r.map((x) => [x.p, ...etapas.map(([, f]) => pct(...f(x), 0))]) }}>
    <Box sx={{ overflowX: "auto" }}>
      <Box component="table" aria-label="Paso entre etapas por provincia" sx={{ borderCollapse: "separate", borderSpacing: 2, fontSize: 13, width: "100%", "& td, & th": { p: 0.75 } }}>
        <thead><tr><td />{etapas.map((e) => <th key={e[0]} scope="col">{e[0]}</th>)}</tr></thead>
        <tbody>{r.map((x) => <tr key={x.p}><th scope="row" style={{ textAlign: "left", fontWeight: 400 }}>{x.p}</th>{etapas.map(([, f], k) => celda(f(x), k))}</tr>)}</tbody>
      </Box>
    </Box>
  </Seccion>;
}

const REVISION: [string, keyof Counts, string][] = [["Aprobadas", "apr", C.teal], ["A subsanar", "sub", C.ambar], ["Rechazadas", "rech", C.rojo], ["Pendientes", "pend", C.gris]];

function Revision({ rows }: { rows: ProvRow[] }) {
  const r = [...rows].sort((a, b) => b.leg - a.leg);
  return <Seccion titulo="Estado de la revisión técnica por provincia"
    tabla={{ head: ["Provincia", "Beneficiarios", ...REVISION.map((s) => s[0])], rows: r.map((x) => [x.p, x.leg, ...REVISION.map(([, k]) => `${fmt(x[k])} (${pct(x[k], x.leg, 0)})`)]) }}>
    <Leyenda items={REVISION.map(([n, , c]) => [n, c])} />
    <Barras max={100} rows={r.map((x) => ({ label: x.p, segments: REVISION.map(([n, k, c]) => {
      const v = x.leg ? (100 * x[k]) / x.leg : 0;
      return { name: n, value: v, color: c, text: v >= 8 ? `${Math.round(v)} %` : "", detail: `${fmt(x[k])} · ${Math.round(v)} %` };
    }) }))} />
  </Seccion>;
}

function BarrasSimples({ titulo, nota, data, unidad, color, pie }: { titulo: string; nota: string; data: [string, number][]; unidad: string; color: string; pie: string }) {
  return <Seccion titulo={titulo} nota={nota} tabla={{ head: ["Categoría", unidad], rows: data.map((d) => [d[0], d[1]]) }} pie={<Nota>{pie}</Nota>}>
    {data.length
      ? <Barras max={Math.max(...data.map((d) => d[1]))} rows={data.map((d) => ({ label: `${d[0]} · ${fmt(d[1])}`, segments: [{ name: unidad, value: d[1], color }] }))} />
      : <Typography variant="body2" color="text.secondary">Sin {unidad} para el filtro elegido.</Typography>}
  </Seccion>;
}

function Expedientes({ todos, seleccionado, onElegir }: { todos: ExpScope[]; seleccionado: string; onElegir: (id: string) => void }) {
  const [verTodos, setVerTodos] = useState(false);
  const orden = [...todos].sort((a, b) => b.porResolver - a.porResolver || b.leg - a.leg);
  const lista = verTodos ? orden : orden.slice(0, 10);
  const usos: Record<string, number> = {};
  orden.forEach((e) => { if (e.n) usos[e.n] = (usos[e.n] || 0) + 1; });
  const sinNro = orden.filter((e) => !e.n).length;
  const repetido = orden.filter((e) => e.n && usos[e.n] > 1).length;
  return <Paper component="section" sx={{ p: 2, minWidth: 0 }}>
    <Typography variant="subtitle1" component="h2" sx={{ fontWeight: 600, mb: 1 }}>
      Expedientes con más casos por resolver <Typography component="span" variant="body2" color="text.secondary">pendientes de revisar + a subsanar · elegí un expediente para filtrar</Typography>
    </Typography>
    <Leyenda items={REVISION.map(([n, , c]) => [n, c])} />
    <Box sx={{ overflowX: "auto" }}>
      <Box component="table" aria-label="Expedientes con más casos por resolver" sx={{ width: "100%", borderCollapse: "collapse", fontSize: 13, "& th, & td": { borderBottom: "1px solid", borderColor: "divider", p: 0.75, textAlign: "left", verticalAlign: "top" } }}>
        <thead><tr>{["Expediente", "Provincia", "Estado", "Días", "Beneficiarios", "Revisión técnica", "Por resolver", "Rechazadas", "Titulares"].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
        <tbody>
          {lista.map((e) => {
            const elegido = String(e.id) === seleccionado;
            const mezcla = REVISION.map(([n, k]) => `${n}: ${fmt(e[k])}`).join(" · ");
            return <Box component="tr" key={e.id} sx={elegido ? { bgcolor: "action.selected" } : undefined}>
              <td>
                <Button size="small" sx={{ p: 0, minWidth: 0, fontWeight: 700 }} aria-pressed={elegido} aria-label={`Filtrar por el expediente #${e.id}`} onClick={() => onElegir(elegido ? "" : String(e.id))}>#{e.id}</Button>
                <Typography component="small" variant="caption" sx={{ display: "block" }} title={e.n}>{e.n ? `cargado como «${e.n}»` : "sin número cargado"}</Typography>
              </td>
              <td>{e.p}</td><td>{estado(e.est)}</td><td>{fmt(e.d)}</td><td>{fmt(e.leg)}</td>
              <td><Box role="img" aria-label={mezcla} title={mezcla} sx={{ display: "flex", height: 12, minWidth: 80, bgcolor: "action.hover", borderRadius: 0.5, overflow: "hidden" }}>
                {REVISION.map(([n, k, c]) => (e[k] && e.leg ? <i key={n} style={{ width: `${(100 * e[k]) / e.leg}%`, background: c }} /> : null))}
              </Box></td>
              <td><b>{fmt(e.porResolver)}</b></td><td>{fmt(e.rech)}</td><td>{fmt(e.tit)} <small>({pct(e.tit, e.leg, 0)})</small></td>
            </Box>;
          })}
        </tbody>
      </Box>
    </Box>
    <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mt: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {sinNro || repetido ? `De ${fmt(orden.length)} expedientes, ${fmt(sinNro)} no tienen número cargado y ${fmt(repetido)} comparten el número con otro: por eso se identifican por el id de SISOC.` : ""}
      </Typography>
      {orden.length > 10 && <Button size="small" variant="outlined" onClick={() => setVerTodos(!verTodos)}>{verTodos ? "Ver los 10 primeros" : `Ver todos (${orden.length})`}</Button>}
    </Stack>
  </Paper>;
}

/* ---------- Screen ---------- */

const grilla = { display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "repeat(2, minmax(0, 1fr))" }, gap: 2 } as const;

export function TableroScreen() {
  const { data, error } = useProjection<TableroData>((body) => !!body.datos && Array.isArray(body.datos.provincias) && Array.isArray(body.datos.expedientes) && typeof body.url_expediente === "string");
  const [prov, setProv] = useState("");
  const [expElegido, setExp] = useState("");
  const vista = useMemo(() => {
    if (!data) return null;
    const { datos } = data;
    const rows = prov ? datos.provincias.filter((r) => r.p === prov) : datos.provincias;
    const expedientes = expedientesEnAlcance(datos.expedientes, prov);
    // An expediente outside the selected province is dropped, as in the native page.
    const elegido = expedientes.find((x) => String(x.id) === expElegido) ?? null;
    // With an expediente chosen, cards and circuit read one row shaped like a province row.
    const det: ProvRow[] | null = elegido ? [{ ...elegido, exp: 1, expProc: elegido.est === "CRUCE_FINALIZADO" ? 0 : 1, per: elegido.leg, cupo: 0 }] : null;
    return { datos, rows, expedientes, elegido, det };
  }, [data, prov, expElegido]);
  if (!data || !vista) return <Loading title="Celiaquía Seguimiento" error={error} />;

  const { datos, rows, expedientes, elegido, det } = vista;
  const exp = elegido ? String(elegido.id) : "";
  const provincias = [...datos.provincias].sort((a, b) => a.p.localeCompare(b.p));
  const opcionesExp = [...expedientes].sort((a, b) => a.p.localeCompare(b.p) || b.id - a.id);
  const rech = sumarCat(datos.rechazo, rows);
  const subs = sumarCat(datos.subsanacion, rows);
  const err = sumarCat(datos.errores, rows);
  const tot = (d: [string, number][]) => d.reduce((a, x) => a + x[1], 0);
  const de = (d: [string, number][], k: string) => (d.find((x) => x[0] === k) || ["", 0])[1];
  const linkExpediente = elegido && data.url_expediente ? internal(data.url_expediente.replace(/\/0\/$/, `/${elegido.id}/`)) : "";

  return <Box component="main" sx={{ p: { xs: 2, md: 3 }, display: "grid", gap: 2 }}>
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between" }}>
      <Box>
        <Typography variant="h5" component="h1" gutterBottom>Celiaquía Seguimiento</Typography>
        <Typography variant="body2">Seguimiento del programa: cuántos hay, dónde se traban y a quién llega. Solo beneficiarios; los responsables no se cuentan.</Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", gap: 1 }} aria-live="polite">
          <Chip size="small" color="primary" id="cel-chip-alcance" label={(prov || "Todas las provincias") + (det ? ` · expediente #${exp}` : "")} />
          <Chip size="small" label={`${fmt(sum(det || rows, "leg"))} personas cargadas`} />
          <Chip size="small" label="Datos en vivo" />
        </Stack>
      </Box>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, minWidth: 180 }}>
          <label htmlFor="cel-filtro-provincia">Provincia</label>
          <select id="cel-filtro-provincia" value={prov} onChange={(e) => { setProv(e.target.value); setExp(""); }} style={{ padding: "6px 8px", font: "inherit" }}>
            <option value="">Todas las provincias</option>
            {provincias.map((r) => <option key={r.p} value={r.p}>{r.p}</option>)}
          </select>
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, minWidth: 180, maxWidth: { sm: 260 } }}>
          <label htmlFor="cel-filtro-expediente">Expediente</label>
          <select id="cel-filtro-expediente" value={exp} aria-describedby="cel-filtro-expediente-ayuda" onChange={(e) => setExp(e.target.value)} style={{ padding: "6px 8px", font: "inherit" }}>
            <option value="">Todos ({fmt(opcionesExp.length)})</option>
            {opcionesExp.map((e) => <option key={e.id} value={String(e.id)}>#{e.id} · {e.p} · {fmt(e.leg)} benef.</option>)}
          </select>
          <FormHelperText id="cel-filtro-expediente-ayuda" sx={{ m: 0 }}>Por id de SISOC: el número cargado no identifica</FormHelperText>
        </Box>
      </Stack>
    </Stack>
    <Messages messages={data.messages} />
    {elegido && <Alert severity="info" role="status">
      <b>Expediente #{elegido.id}</b> ({elegido.p} · {estado(elegido.est)} · creado hace {fmt(elegido.d)} días): las tarjetas y el circuito muestran solo este expediente; el resto de los bloques sigue mostrando {prov || "todas las provincias"}.
      <Stack direction="row" spacing={2} sx={{ mt: 1 }} component="span">
        {linkExpediente && <a href={linkExpediente}>Abrir en SISOC</a>}
        <Button size="small" onClick={() => setExp("")} sx={{ p: 0, minWidth: 0 }}>Quitar filtro</Button>
      </Stack>
    </Alert>}
    <Kpis rows={det || rows} />
    <Box sx={grilla}><Cupo rows={rows} /><Piramide rows={rows} datos={datos} /></Box>
    <Box sx={grilla}><Embudo rows={det || rows} /><Conversion rows={rows} /></Box>
    <Expedientes todos={expedientes} seleccionado={exp} onElegir={setExp} />
    <Box sx={grilla}>
      <Revision rows={rows} />
      <BarrasSimples titulo="Errores al importar el Excel" nota="filas que no se pudieron cargar" data={err} unidad="filas" color={C.gris2}
        pie={tot(err) ? `"Corregido o sin mensaje": SISOC borra el mensaje cuando el registro se corrige o se procesa (${fmt(de(err, "Corregido o sin mensaje"))} de ${fmt(tot(err))}).` : ""} />
    </Box>
    <Box sx={grilla}>
      <BarrasSimples titulo="Motivos de rechazo" nota="rechazadas que mencionan cada motivo" data={rech} unidad="rechazadas" color={C.rojo}
        pie={tot(rech) ? `${fmt(de(rech, "Sin motivo registrado"))} de ${fmt(sum(rows, "rech"))} rechazadas no tienen motivo registrado. Una rechazada puede mencionar más de un motivo: las barras suman ${fmt(tot(rech))}.` : ""} />
      <BarrasSimples titulo="Motivos de subsanación" nota="observaciones por tipo" data={subs} unidad="observaciones" color={C.ambar}
        pie={tot(subs) ? `El ${pct(de(subs, "Otros"), tot(subs), 0)} cae en "Otros": el tipo no alcanza para clasificar.` : ""} />
    </Box>
    <span style={srOnly} aria-live="polite">{elegido ? `Filtrado por el expediente #${elegido.id}` : ""}</span>
  </Box>;
}
