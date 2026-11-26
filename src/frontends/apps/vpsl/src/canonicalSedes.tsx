import { useState, type FormEvent, type ReactNode, type Dispatch, type SetStateAction } from "react";
import { Button, MenuItem, Stack, TextField } from "@mui/material";
import { ApiError, type Page, type Sede } from "./api";
import { CANONICAL_ROOT } from "./canonicalRoutes";

export const CANONICAL_SEDES = `${CANONICAL_ROOT}sedes/`;
type Filter = { field: string; op: string; value: string; empty_mode?: string };
type FilterField = { name: string; label: string; type: string; choices?: { value: string; label: string }[] };
export type AdvancedFilterConfig = { fields: FilterField[]; operators: Record<string, string[]> };
export type SedesFilterConfig = AdvancedFilterConfig;
export type CanonicalSedesPage = Page<Sede> & { page: number; pages: number; page_size: number; filters_config: SedesFilterConfig };

export async function loadCanonicalList<T>(url: string, label: string): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiError(response.status, response.status === 404 ? "La página solicitada no existe." : `No se pudo cargar el listado de ${label}.`);
  if (!response.headers.get("Content-Type")?.startsWith("application/json")) throw new Error(`El listado de ${label} requiere una versión compatible del servidor.`);
  return response.json();
}

export type AdvancedFiltersState = { logic: string; items: Filter[] };

export function loadCanonicalSedes(search: string): Promise<CanonicalSedesPage> {
  return loadCanonicalList(CANONICAL_SEDES + search, "sedes");
}

export function readFilters(search: string): AdvancedFiltersState {
  try {
    const raw = JSON.parse(new URLSearchParams(search).get("filters") || "{}");
    return { logic: raw.logic === "OR" ? "OR" : "AND", items: Array.isArray(raw.items) ? raw.items.filter((item: Filter) => item && typeof item.field === "string" && typeof item.op === "string").map((item: Filter) => ({ ...item, value: String(item.value ?? "") })) : [] };
  } catch { return { logic: "AND", items: [] }; }
}

const OP_LABELS: Record<string, string> = { contains: "Contiene", ncontains: "No contiene", eq: "Es igual a", ne: "Es distinto de", gt: "Mayor que", lt: "Menor que", gte: "Desde", lte: "Hasta", empty: "Está vacío" };

export function CanonicalSedesFilters({ search, config, onApply }: { search: string; config?: SedesFilterConfig; onApply: (params: URLSearchParams) => void }) {
  const [query, setQuery] = useState(() => new URLSearchParams(search).get("busqueda") || "");
  const [filters, setFilters] = useState(() => readFilters(search));
  function submit(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams(search);
    params.delete("page");
    params.delete("sede");
    if (query) params.set("busqueda", query); else params.delete("busqueda");
    if (filters.items.length) params.set("filters", JSON.stringify(filters)); else params.delete("filters");
    onApply(params);
  }
  return <form onSubmit={submit}>
    <Stack spacing={2}>
      <TextField label="Buscar sede" value={query} onChange={event => setQuery(event.target.value)} placeholder="Nombre, CUE, jurisdicción, localidad o domicilio" />
      <AdvancedFilterControls filters={filters} onChange={setFilters} config={config}>
        <Button type="submit" variant="contained">Aplicar filtros</Button>
        <Button type="button" onClick={() => {
          const params = new URLSearchParams(search);
          for (const key of ["busqueda", "filters", "page"]) params.delete(key);
          onApply(params);
        }}>Limpiar filtros</Button>
      </AdvancedFilterControls>
    </Stack>
  </form>;
}


export function AdvancedFilterControls({ filters, onChange, config, children }: { filters: AdvancedFiltersState; onChange: Dispatch<SetStateAction<AdvancedFiltersState>>; config?: AdvancedFilterConfig; children: ReactNode }) {
  function update(index: number, patch: Partial<Filter>) {
    onChange(current => ({ ...current, items: current.items.map((item, position) => position === index ? { ...item, ...patch } : item) }));
  }
  return <>
      <TextField select label="Combinar filtros" value={filters.logic} onChange={event => onChange(current => ({ ...current, logic: event.target.value }))}>
        <MenuItem value="AND">Todos los campos</MenuItem><MenuItem value="OR">Cualquier campo</MenuItem>
      </TextField>
      {filters.items.map((item, index) => {
        const field = config?.fields.find(candidate => candidate.name === item.field);
        return <Stack key={index} spacing={1} direction={{ xs: "column", md: "row" }}>
          <TextField select fullWidth label={`Campo del filtro ${index + 1}`} value={item.field} onChange={event => {
            const next = config?.fields.find(candidate => candidate.name === event.target.value);
            update(index, { field: event.target.value, op: config?.operators[next?.type || "text"]?.[0] || "eq", value: "" });
          }}>
            {!field && <MenuItem value={item.field}>{item.field}</MenuItem>}
            {config?.fields.map(candidate => <MenuItem key={candidate.name} value={candidate.name}>{candidate.label}</MenuItem>)}
          </TextField>
          <TextField select fullWidth label={`Operador del filtro ${index + 1}`} value={item.op} onChange={event => update(index, { op: event.target.value })}>
            {(config?.operators[field?.type || "text"] || [item.op]).map(op => <MenuItem key={op} value={op}>{OP_LABELS[op] || op}</MenuItem>)}
          </TextField>
          {item.op === "empty" ? <TextField select fullWidth label={`Vacío del filtro ${index + 1}`} value={field?.type === "text" ? item.empty_mode || "both" : "null"} onChange={event => update(index, { empty_mode: event.target.value })}>
            {field?.type === "text" && <MenuItem value="both">Nulo o texto vacío</MenuItem>}<MenuItem value="null">Solo nulo</MenuItem>{field?.type === "text" && <MenuItem value="blank">Solo texto vacío</MenuItem>}
          </TextField> : <TextField fullWidth select={Boolean(field?.choices)} type={field?.type === "number" ? "number" : field?.type === "date" ? "date" : "text"} label={`Valor del filtro ${index + 1}`} value={item.value} onChange={event => update(index, { value: event.target.value })}>
            {field?.choices?.map(choice => <MenuItem key={choice.value} value={choice.value}>{choice.label}</MenuItem>)}
          </TextField>}
          <Button type="button" onClick={() => onChange(current => ({ ...current, items: current.items.filter((_, position) => position !== index) }))} aria-label={`Quitar filtro ${index + 1}`}>Quitar</Button>
        </Stack>;
      })}
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        <Button type="button" disabled={!config} onClick={() => {
          const field = config?.fields[0];
          if (field) onChange(current => ({ ...current, items: [...current.items, { field: field.name, op: config?.operators[field.type]?.[0] || "eq", value: "" }] }));
        }}>Agregar filtro</Button>
        {children}
      </Stack>
  </>;
}
