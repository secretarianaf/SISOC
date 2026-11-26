import { useEffect, useMemo, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";

export const CANONICAL_EXPEDIENTES_PATH = "/celiaquia/expedientes/";
type Choice = { value: string; label: string };
type FilterField = { name: string; label: string; type: string; choices?: Choice[] };
type FilterItem = { field: string; op: string; value: string };
type Person = { id: number; name: string };
type Action = { label: string; url: string; method: "GET" | "POST" | "DELETE" };
type Row = {
  id: number; numero: string; fecha: string; provincia: string; estado: string;
  subsanar: number; subsanado: number; tecnicos: Person[]; can_assign: boolean;
  excel: { url: string; cargado_por: string | null; procesado_por: string | null } | null;
  actions: Action[]; urls: { detail: string; assign: string };
};
type Data = {
  version: number; title: string; create_url: string | null; show_tecnicos: boolean;
  show_excel: boolean; show_audit: boolean; tecnicos: Person[]; rows: Row[];
  filters: { fields: FilterField[]; operators: Record<string, string[]>; defaultOperators: Record<string, string> };
};

function internal(url: string) {
  if (!url.startsWith("/") || url.startsWith("//") || url.includes("\\")) throw new Error("URL de navegación inválida.");
  return url;
}

function initialFilters(): { logic: string; items: FilterItem[] } {
  try {
    const value = JSON.parse(new URLSearchParams(window.location.search).get("filters") ?? "{}");
    return { logic: value.logic === "OR" ? "OR" : "AND", items: Array.isArray(value.items) ? value.items : [] };
  } catch {
    return { logic: "AND", items: [] };
  }
}

const OP_LABELS: Record<string, string> = {
  contains: "Contiene", ncontains: "No contiene", eq: "Igual a", ne: "Distinto de", gt: "Mayor que", lt: "Menor que", empty: "Vacío",
};

function Filters({ data }: { data: Data }) {
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("q") ?? "");
  const [filters, setFilters] = useState(initialFilters);
  const fields = data.filters.fields;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const params = new URLSearchParams(window.location.search);
    params.delete("q"); params.delete("filters"); params.delete("page");
    if (query) params.set("q", query);
    if (filters.items.length) params.set("filters", JSON.stringify(filters));
    window.location.assign(CANONICAL_EXPEDIENTES_PATH + (params.size ? `?${params}` : ""));
  };
  const update = (index: number, item: FilterItem) => setFilters((previous) => ({ ...previous, items: previous.items.map((old, i) => i === index ? item : old) }));
  return <form onSubmit={submit} aria-label="Buscar y filtrar expedientes" className="canonical-filters">
    <label>Buscar <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
    <label>Combinar filtros <select value={filters.logic} onChange={(e) => setFilters({ ...filters, logic: e.target.value })}>
      <option value="AND">Todas las condiciones</option><option value="OR">Cualquier condición</option>
    </select></label>
    {filters.items.map((item, index) => {
      const field = fields.find((candidate) => candidate.name === item.field);
      if (!field) return <p key={index} role="alert">Filtro no disponible: {item.field}. <button type="button" onClick={() => setFilters({ ...filters, items: filters.items.filter((_, i) => i !== index) })}>Quitar</button></p>;
      return <fieldset key={index}><legend>Condición {index + 1}</legend>
        <label>Campo <select value={item.field} onChange={(e) => {
          const next = fields.find((candidate) => candidate.name === e.target.value)!;
          update(index, { field: next.name, op: data.filters.defaultOperators[next.type], value: "" });
        }}>{fields.map((candidate) => <option key={candidate.name} value={candidate.name}>{candidate.label}</option>)}</select></label>
        <label>Operador <select value={item.op} onChange={(e) => update(index, { ...item, op: e.target.value })}>{data.filters.operators[field.type].map((op) => <option key={op} value={op}>{OP_LABELS[op] ?? op}</option>)}</select></label>
        {item.op !== "empty" && <label>Valor {field.choices ? <select value={item.value} onChange={(e) => update(index, { ...item, value: e.target.value })}>
          <option value="">Seleccionar</option>{field.choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
        </select> : <input type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"} value={item.value} onChange={(e) => update(index, { ...item, value: e.target.value })} />}</label>}
        <button type="button" onClick={() => setFilters({ ...filters, items: filters.items.filter((_, i) => i !== index) })}>Quitar condición {index + 1}</button>
      </fieldset>;
    })}
    {fields.length > 0 && <button type="button" onClick={() => setFilters({ ...filters, items: [...filters.items, { field: fields[0].name, op: data.filters.defaultOperators[fields[0].type], value: "" }] })}>Agregar filtro</button>}
    <button type="submit">Buscar</button> <a href={CANONICAL_EXPEDIENTES_PATH}>Limpiar filtros</a>
  </form>;
}

export function CanonicalExpedientesList() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [sort, setSort] = useState<{ field: "id" | "numero" | "fecha" | "provincia" | "estado"; ascending: boolean } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(window.location.pathname + window.location.search, { credentials: "same-origin", headers: { Accept: "application/json" }, signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`No se pudo cargar el listado (${response.status}).`);
        const body = await response.json() as Data;
        if (body.version !== 1 || !Array.isArray(body.rows) || !body.filters) throw new Error("El listado no es compatible con esta versión.");
        setData(body);
      }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "No se pudo cargar el listado."); });
    return () => controller.abort();
  }, []);
  const rows = useMemo(() => {
    if (!data) return [];
    if (!sort) return data.rows;
    return [...data.rows].sort((left, right) => {
      const a = left[sort.field], b = right[sort.field];
      const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "es", { numeric: true });
      return sort.ascending ? result : -result;
    });
  }, [data, sort]);

  const mutate = async (url: string, method: "POST" | "DELETE", body?: URLSearchParams) => {
    if (pending || uncertain) return;
    setPending(true); setError("");
    const request = async (target: string) => {
      const response = await fetch(internal(target), { method, credentials: "same-origin", headers: {
        "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest", ...(body ? { "Content-Type": "application/x-www-form-urlencoded" } : {}),
      }, body });
      const result = await response.json();
      if (!response.ok || result.success === false) throw new Error(result.error ?? `La acción fue rechazada (${response.status}).`);
      return result;
    };
    try {
      if (method === "DELETE") {
        const preview = await request(url + (url.includes("?") ? "&" : "?") + "preview=1");
        const summary = preview.preview;
        if (!summary) throw new Error("No se pudo obtener la vista previa. No se eliminó ningún registro.");
        const detail = (summary.desglose_por_modelo ?? []).map((item: { modelo: string; cantidad: number; modo: string }) => `${item.modelo}: ${item.cantidad} (${item.modo})`).join("\n");
        if (!window.confirm(`¿Confirmar eliminación? Registros afectados: ${summary.total_afectados}\n${detail}`)) return;
      }
      await request(url);
      window.location.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo confirmar el resultado. Recargue antes de reintentar.");
      // A transport failure after dispatch can have committed: never auto-retry.
      if (cause instanceof TypeError) setUncertain(true);
    } finally { setPending(false); }
  };
  if (!data) return <main><h1>Expedientes de Celiaquía</h1>{error ? <p role="alert">{error}</p> : <p role="status">Cargando…</p>}</main>;
  const disabled = pending || uncertain;
  return <main className="canonical-expedientes">
    <style>{`.canonical-expedientes{max-width:1400px;margin:auto;padding:1rem}.canonical-expedientes button,.canonical-expedientes input,.canonical-expedientes select{font:inherit;padding:.45rem;margin:.2rem;max-width:100%}.canonical-expedientes a{display:inline-block;margin:.3rem}.canonical-filters{display:flex;gap:.6rem;align-items:end;flex-wrap:wrap;margin-block:1rem}.canonical-filters fieldset{display:flex;flex-wrap:wrap;gap:.5rem}.canonical-expedientes table{width:100%;border-collapse:collapse;min-width:800px}.canonical-expedientes td,.canonical-expedientes th{padding:.7rem;text-align:left;border-bottom:1px solid #aab2bd}.canonical-expedientes :focus-visible{outline:3px solid #1263b5;outline-offset:2px}`}</style>
    <h1>{data.title}</h1>
    <nav aria-label="Navegación de Celiaquía"><a href="/">Inicio</a> <a href="/reporter-provincias/">Reporte</a></nav>
    {data.create_url && <a href={internal(data.create_url)}>Nuevo expediente</a>}
    <Filters data={data} />
    {error && <p role="alert">{error}</p>}
    {uncertain && <p role="alert">Resultado incierto. Recargue la página antes de volver a operar.</p>}
    <p>{rows.length} expedientes</p>
    <div style={{ overflowX: "auto" }} tabIndex={0} role="region" aria-label="Listado de expedientes">
      <table><thead><tr>{([['id', 'ID'], ['numero', 'Número de expediente'], ['fecha', 'Fecha creación'], ['provincia', 'Provincia'], ['estado', 'Estado']] as const).map(([field, label]) => <th key={field} scope="col" aria-sort={sort?.field === field ? sort.ascending ? "ascending" : "descending" : "none"}><button onClick={() => setSort({ field, ascending: sort?.field === field ? !sort.ascending : true })}>{label}</button></th>)}
        {data.show_tecnicos && <th scope="col">Técnico</th>}{data.show_excel && <th scope="col">Excel original</th>}<th scope="col">Acciones</th>
      </tr></thead><tbody>{rows.map((row) => <tr key={row.id}>
        <td>{row.id}</td><td>{row.numero}</td><td>{new Date(row.fecha).toLocaleString("es-AR")}</td><td>{row.provincia}</td>
        <td>{row.estado}{row.subsanar > 0 && <div>{row.subsanar} a subsanar</div>}{row.subsanado > 0 && <div>{row.subsanado} subsanados</div>}</td>
        {data.show_tecnicos && <td>{row.can_assign && <form onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void mutate(row.urls.assign, "POST", new URLSearchParams({ tecnico_id: String(form.get("tecnico_id")) })); }}>
          <label>Técnico para expediente {row.id}<select name="tecnico_id" required disabled={disabled} defaultValue=""><option value="">Agregar técnico</option>{data.tecnicos.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label><button disabled={disabled}>Asignar</button>
        </form>}{row.tecnicos.map((person) => <div key={person.id}>{person.name}{row.can_assign && <button disabled={disabled} onClick={() => void mutate(`${row.urls.assign}?tecnico_id=${person.id}`, "DELETE")} aria-label={`Quitar ${person.name} del expediente ${row.id}`}>Quitar</button>}</div>)}</td>}
        {data.show_excel && <td>{row.excel ? <><a href={internal(row.excel.url)}>Excel original</a>{data.show_audit && <><div>Cargado por {row.excel.cargado_por ?? "Carga sin usuario"}</div><div>{row.excel.procesado_por ? `Procesado por ${row.excel.procesado_por}` : "Sin procesamiento"}</div></>}</> : "-"}</td>}
        <td><a href={internal(row.urls.detail)}>Ver</a>{row.actions.map((action) => action.method === "GET" ? <a key={action.label} href={internal(action.url)}>{action.label}</a> : <button key={action.label} disabled={disabled} onClick={() => void mutate(action.url, action.method as "POST" | "DELETE")}>{action.label}</button>)}</td>
      </tr>)}</tbody></table>
      {rows.length === 0 && <p>No hay expedientes que coincidan con el filtro.</p>}
    </div>
  </main>;
}
