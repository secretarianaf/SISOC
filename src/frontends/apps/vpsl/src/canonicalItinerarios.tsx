import { useState, type FormEvent } from "react";
import { Button, MenuItem, Stack, TextField } from "@mui/material";
import type { Page, Itinerario } from "./api";
import { CANONICAL_ROOT } from "./canonicalRoutes";
import { AdvancedFilterControls, loadCanonicalList, readFilters, type AdvancedFilterConfig } from "./canonicalSedes";

export type CanonicalItinerariosPage = Page<Itinerario> & {
  page: number;
  pages: number;
  page_size: number;
  filters_config: AdvancedFilterConfig;
  provincias: { id: number; nombre: string }[];
  provincia_restringida: { id: number; nombre: string } | null;
};

export function loadCanonicalItinerarios(search: string): Promise<CanonicalItinerariosPage> {
  return loadCanonicalList(CANONICAL_ROOT + search, "itinerarios");
}

const SIMPLE_KEYS = ["busqueda", "buscar_por", "estado", "provincia", "localidad", "fecha_desde", "fecha_hasta"] as const;
const SEARCH_FIELDS = [ ["todos", "Todos"], ["codigo", "Código"], ["provincia", "Provincia"], ["estado", "Estado"], ["referente", "Referente"] ];

export function CanonicalItinerariosFilters({ search, data, onApply }: { search: string; data?: CanonicalItinerariosPage; onApply: (params: URLSearchParams) => void }) {
  const [simple, setSimple] = useState(() => {
    const params = new URLSearchParams(search);
    return Object.fromEntries(SIMPLE_KEYS.map(key => [key, params.get(key) || (key === "buscar_por" ? "todos" : "")])) as Record<typeof SIMPLE_KEYS[number], string>;
  });
  const [filters, setFilters] = useState(() => readFilters(search));
  const update = (key: typeof SIMPLE_KEYS[number], value: string) => setSimple(current => ({ ...current, [key]: value }));
  function submit(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams(search);
    params.delete("page");
    for (const key of SIMPLE_KEYS) {
      if (simple[key] && !(key === "provincia" && data?.provincia_restringida)) params.set(key, simple[key]);
      else params.delete(key);
    }
    if (filters.items.length) params.set("filters", JSON.stringify(filters)); else params.delete("filters");
    onApply(params);
  }
  return <form onSubmit={submit}>
    <Stack spacing={2}>
      <TextField label="Buscar itinerarios" value={simple.busqueda} onChange={event => update("busqueda", event.target.value)} placeholder="Código, provincia, estado, referente o sede" />
      <TextField select label="Buscar por" value={simple.buscar_por} onChange={event => update("buscar_por", event.target.value)}>
        {SEARCH_FIELDS.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      <TextField select label="Estado" value={simple.estado} onChange={event => update("estado", event.target.value)}>
        <MenuItem value="">Todos</MenuItem>
        {data?.estados?.map(option => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
      </TextField>
      {data?.provincia_restringida ? <TextField label="Provincia" value={data.provincia_restringida.nombre} disabled /> : <TextField select label="Provincia" value={simple.provincia} onChange={event => update("provincia", event.target.value)}>
        <MenuItem value="">Todas</MenuItem>
        {data?.provincias.map(province => <MenuItem key={province.id} value={String(province.id)}>{province.nombre}</MenuItem>)}
      </TextField>}
      <TextField label="Localidad" value={simple.localidad} onChange={event => update("localidad", event.target.value)} />
      <TextField type="date" label="Fecha desde" value={simple.fecha_desde} onChange={event => update("fecha_desde", event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
      <TextField type="date" label="Fecha hasta" value={simple.fecha_hasta} onChange={event => update("fecha_hasta", event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
      <AdvancedFilterControls filters={filters} onChange={setFilters} config={data?.filters_config}>
        <Button type="submit" variant="contained">Aplicar filtros</Button>
        <Button type="button" onClick={() => {
          const params = new URLSearchParams(search);
          for (const key of [...SIMPLE_KEYS, "filters", "page"]) params.delete(key);
          onApply(params);
        }}>Limpiar filtros</Button>
      </AdvancedFilterControls>
    </Stack>
  </form>;
}
