/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState } from "react";
import { record, text, webClient } from "./MainFrame";

/**
 * CM02.02 recipients panel: `partials/destinatarios_panel.html` plus `comunicadosDestinatarios.js`.
 * Combinable filters go to `web/comedores/comunicados/destinatarios/<universo>/buscar|todos/`,
 * which return the native JSON; the chosen ids travel as one hidden CSV input named after the universe.
 */
export type FilterField = { name: string; label: string; type?: string; choices?: { value: string; label: string }[]; input?: { step?: string } };
export type FilterConfig = { fields?: FilterField[]; operators?: Record<string, string[]>; defaultField?: string };
export type Selected = { id: number; nombre: string };
type Row = { key: number; campo: string; op: string; valor: string };
type Result = { results: { id: number; nombre: string; detalle?: string }[]; total: number; has_more: boolean; page: number };

const API = "web/comedores/comunicados/destinatarios/";
const OPERATOR_LABELS: Record<string, string> = {
  contains: "contiene", ncontains: "no contiene", eq: "es igual a", ne: "es distinto de", gt: "mayor que", lt: "menor que",
  gte: "mayor o igual", lte: "menor o igual", empty: "está vacío",
};
const BOOLEANS = [{ value: "true", label: "Sí" }, { value: "false", label: "No" }];
const HINT = "Usá los filtros y presioná Buscar.";

export const resultValid = (v: unknown): v is Result =>
  record(v) && Array.isArray(v.results) && v.results.every((r) => record(r) && Number.isSafeInteger(r.id) && text(r.nombre)) &&
  typeof v.total === "number" && typeof v.has_more === "boolean";

let rowKey = 0;

export function DestinatariosPanel({ universo, config, initial, errors }: { universo: string; config: FilterConfig; initial: Selected[]; errors: string[] }) {
  const fields = Array.isArray(config.fields) ? config.fields : [];
  const byName = (name: string) => fields.find((f) => f.name === name);
  const opsFor = (name: string) => config.operators?.[byName(name)?.type ?? "text"] ?? ["eq"];
  const newRow = (): Row => {
    const campo = config.defaultField && byName(config.defaultField) ? config.defaultField : fields[0]?.name ?? "";
    return { key: ++rowKey, campo, op: opsFor(campo)[0], valor: "" };
  };
  const [rows, setRows] = useState<Row[]>(() => (fields.length ? [newRow()] : []));
  const [selection, setSelection] = useState<[string, string][]>(() => initial.map((s) => [String(s.id), s.nombre]));
  const [result, setResult] = useState<Result | null>(null);
  const [summary, setSummary] = useState(HINT);
  const [allHidden, setAllHidden] = useState(true);
  const [allDisabled, setAllDisabled] = useState(false);
  const last = useRef<string | null>(null);
  const loading = useRef(false);
  const chosen = new Set(selection.map(([id]) => id));
  // `comunicadosDestinatarios.js` returns before `init()` without filter fields: the panel stays inert and keeps the server input.
  const inert = fields.length === 0;

  const collect = () => {
    const items: Record<string, string>[] = [];
    for (const row of rows) {
      const field = byName(row.campo);
      if (!field) continue;
      if (row.op === "empty") { items.push({ field: row.campo, op: row.op }); continue; }
      const valor = (field.type === "choice" || field.type === "boolean" ? row.valor : row.valor.trim());
      if (valor !== "") items.push({ field: row.campo, op: row.op, value: valor });
    }
    return JSON.stringify({ logic: "AND", items });
  };
  const patch = (key: number, change: Partial<Row>) => setRows((all) => all.map((r) => (r.key === key ? { ...r, ...change } : r)));

  async function search(page: number, reuse?: boolean) {
    if (loading.current) return;
    if (!reuse || last.current === null) last.current = collect();
    loading.current = true;
    setSummary("Buscando...");
    try {
      const { data } = await webClient.get(`${API}${universo}/buscar/`, { params: { filters: last.current, page } });
      if (!resultValid(data)) throw new Error("invalid");
      setResult(data);
      setSummary(data.total === 0 ? "No se encontraron resultados con esos filtros." : `${data.total} resultado(s) encontrado(s).`);
      setAllHidden(data.total <= 0);
    } catch {
      setSummary("No se pudo completar la búsqueda. Intentá nuevamente.");
      setResult(null);
    } finally {
      loading.current = false;
    }
  }

  async function addAll() {
    if (loading.current || last.current === null) return;
    loading.current = true; setAllDisabled(true);
    try {
      const { data } = await webClient.get(`${API}${universo}/todos/`, { params: { filters: last.current } });
      if (record(data) && data.truncado) {
        setSummary(`Son ${data.total} resultados y el máximo para agregar de una vez es ${data.max_seleccion_masiva}. Afiná los filtros.`);
      } else if (record(data) && Array.isArray(data.results)) {
        setSelection((all) => {
          const map = new Map(all);
          for (const item of data.results as Selected[]) map.set(String(item.id), item.nombre);
          return [...map];
        });
      }
    } catch {
      // The native panel only logs this failure.
    } finally {
      loading.current = false; setAllDisabled(false);
    }
  }

  const toggle = (id: string, nombre: string) => setSelection((all) => (all.some(([i]) => i === id) ? all.filter(([i]) => i !== id) : [...all, [id, nombre]]));
  const clear = () => { setRows([newRow()]); last.current = null; setResult(null); setAllHidden(true); setSummary(HINT); };

  return (
    <div className="destinatarios-panel" data-universo={universo}>
      <div className="destinatarios-filtros">
        <div className="destinatarios-filtros__rows">
          {rows.map((row, index) => {
            const field = byName(row.campo) ?? fields[0];
            const type = field?.type ?? "text";
            const choice = type === "choice" || type === "boolean";
            const empty = row.op === "empty";
            return (
              <div className="destinatarios-filtro-row" key={row.key}>
                <select className="form-select destinatarios-filtro__campo" aria-label="Filtrar por" value={row.campo}
                  onChange={(e) => patch(row.key, { campo: e.target.value, op: opsFor(e.target.value)[0], valor: "" })}>
                  {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
                </select>
                <select className="form-select destinatarios-filtro__op" aria-label="Tipo de coincidencia" value={row.op} onChange={(e) => patch(row.key, { op: e.target.value })}>
                  {opsFor(row.campo).map((op) => <option key={op} value={op}>{OPERATOR_LABELS[op] ?? op}</option>)}
                </select>
                <input type={type === "number" ? "number" : type === "date" ? "date" : "text"} className="form-control destinatarios-filtro__valor" autoComplete="off"
                  aria-label="Valor a buscar" placeholder={`Valor del filtro ${index + 1}`} step={type === "number" ? field?.input?.step : undefined}
                  hidden={choice || empty} value={choice ? "" : row.valor} onChange={(e) => patch(row.key, { valor: e.target.value })}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void search(1); } }} />
                <select className="form-select destinatarios-filtro__valor" aria-label="Valor a buscar" hidden={!choice || empty} value={choice ? row.valor : ""}
                  onChange={(e) => patch(row.key, { valor: e.target.value })}>
                  <option value="">Seleccionar</option>
                  {(type === "boolean" ? BOOLEANS : field?.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <button type="button" className="btn btn-sm btn-outline-secondary" aria-label="Quitar filtro" hidden={rows.length <= 1}
                  onClick={() => setRows((all) => (all.length > 1 ? all.filter((r) => r.key !== row.key) : all))}><i className="fas fa-minus" /></button>
              </div>
            );
          })}
        </div>
        <div className="destinatarios-filtros__acciones">
          <button type="button" className="btn btn-sm btn-outline-light" onClick={() => setRows((all) => [...all, newRow()])}><i className="fas fa-plus me-1" />Filtro</button>
          <button type="button" className="btn btn-sm btn-outline-light" onClick={clear}><i className="fas fa-eraser me-1" />Limpiar</button>
          <button type="button" className="btn btn-sm btn-warning" onClick={() => void search(1)}><i className="fas fa-search me-1" />Buscar</button>
        </div>
        <small className="form-text d-block">Los filtros se combinan entre sí (AND). Buscá, elegí, y volvé a filtrar para seguir sumando destinatarios.</small>
      </div>
      <div className="destinatarios-resultados">
        <div className="destinatarios-resultados__head">
          <span className="destinatarios-resumen">{summary}</span>
          <button type="button" className="btn btn-sm btn-outline-warning" hidden={allHidden} disabled={allDisabled} onClick={() => void addAll()}>
            <i className="fas fa-layer-group me-1" />Agregar todos los resultados
          </button>
        </div>
        <div className="comedores-lista-container">
          {result?.results.map((item) => {
            const id = String(item.id), on = chosen.has(id);
            return (
              <div className="comedor-row" key={id}>
                <span className="comedor-nombre">{item.nombre}{item.detalle && <><br /><small className="destinatarios-detalle">{item.detalle}</small></>}</span>
                <button type="button" className={on ? "btn btn-sm btn-outline-danger" : "btn btn-sm btn-outline-warning"} onClick={() => toggle(id, item.nombre)}>
                  <i className={on ? "fas fa-times" : "fas fa-plus"} />{" "}{on ? "Quitar" : "Agregar"}
                </button>
              </div>
            );
          })}
        </div>
        <div className="destinatarios-paginacion">
          {result && (result.page > 1 || result.has_more) && <>
            <button type="button" className="btn btn-sm btn-outline-light" disabled={result.page <= 1} onClick={() => void search(result.page - 1, true)}>Anterior</button>
            <span className="destinatarios-pagina">Página {result.page}</span>
            <button type="button" className="btn btn-sm btn-outline-light" disabled={!result.has_more} onClick={() => void search(result.page + 1, true)}>Siguiente</button>
          </>}
        </div>
      </div>
      <div className="destinatarios-seleccion">
        <label>
          Seleccionados (<span>{inert ? "" : selection.length}</span>){" "}
          <button type="button" className="btn btn-sm btn-link text-danger p-0 ms-2" onClick={() => setSelection([])}>Quitar todos</button>
        </label>
        <div className="comedores-badges mb-2">
          {inert ? null : selection.length ? selection.map(([id, nombre]) => (
            <span className="badge me-1 mb-1 d-inline-flex align-items-center gap-1" key={id}>
              {nombre}{" "}
              <button type="button" className="btn-close btn-close-white" style={{ fontSize: "0.55em" }} aria-label={`Quitar ${nombre}`} onClick={() => toggle(id, nombre)} />
            </span>
          )) : <p className="small mb-0" style={{ color: "#6b7280" }}>No hay destinatarios seleccionados.</p>}
        </div>
        <div className="d-none"><input type="hidden" name={universo} id={inert ? `id_${universo}` : undefined} value={selection.map(([id]) => id).join(",")} readOnly={inert} /></div>
        {errors.length > 0 && <div className="invalid-feedback d-block">{errors[0]}</div>}
      </div>
    </div>
  );
}
