/* eslint-disable react-refresh/only-export-components -- the filters bar exports its config validator with the component. */
import { useRef, useState } from "react";
import { record, text } from "./cdfFrame";

/**
 * `search_bar.html` in filters mode with `advanced_filters.js`: one full bar per
 * filter, the operator taken from the field type, `boolean`/`choice` fields
 * with a value select ("Sí"/"No" by default). The form stays a native GET.
 */
type Option = { value: string; label: string };
export type FilterField = { name: string; label: string; type: string; input?: { step?: string; min?: string; max?: string }; options?: Option[]; choices?: Option[] };
export type FiltersConfig = { fields: FilterField[]; defaultOperators?: Record<string, string>; defaultField?: string; booleanOptions?: Option[] };
export type Favorites = { section: string; url: string; detail_url_template: string };

export const filtersConfigValid = (v: unknown): v is FiltersConfig => record(v) && Array.isArray(v.fields) && v.fields.length > 0 &&
  v.fields.every((f) => record(f) && text(f.name) && text(f.label) && text(f.type));

type Row = { key: number; field: string; value: string };
type Prefill = { field?: unknown; value?: unknown };

function choiceOptions(field: FilterField, config: FiltersConfig): Option[] {
  if (field.options?.length) return field.options;
  if (field.type === "boolean") return config.booleanOptions ?? [{ value: "true", label: "Sí" }, { value: "false", label: "No" }];
  return field.choices ?? [];
}
const isChoice = (field: FilterField) => field.type === "choice" || field.type === "boolean";

function initialRows(config: FiltersConfig, byName: Map<string, FilterField>): Row[] {
  const fallback = config.defaultField && byName.has(config.defaultField) ? config.defaultField : "";
  const valueFor = (field: string, value = "") => {
    const definition = byName.get(field) ?? config.fields[0];
    return isChoice(definition) && value === "" ? choiceOptions(definition, config)[0]?.value ?? "" : value;
  };
  const blank = (key: number): Row => ({ key, field: fallback, value: valueFor(fallback) });
  try {
    const raw = new URLSearchParams(window.location.search).get("filters");
    if (!raw) return [blank(0)];
    const parsed: unknown = JSON.parse(raw);
    if (!record(parsed) || !Array.isArray(parsed.items) || !parsed.items.length) return [blank(0)];
    return parsed.items.map((item: Prefill, index: number) => (record(item) && text(item.field) && byName.has(item.field)
      ? { key: index, field: item.field, value: valueFor(item.field, item.value === undefined ? "" : String(item.value)) }
      : blank(index)));
  } catch {
    return [blank(0)];
  }
}

export function Filters({ config, action, favorites }: { config: FiltersConfig; action: string; favorites: Favorites }) {
  const fields = config.fields.filter((f) => f.name && f.label);
  const byName = new Map(fields.map((f) => [f.name, f]));
  const defaults: Record<string, string> = { text: "contains", number: "eq", date: "eq", boolean: "eq", choice: "eq", ...config.defaultOperators };
  const [rows, setRows] = useState(() => initialRows(config, byName));
  const next = useRef(rows.length);
  const hidden = useRef<HTMLInputElement>(null);
  const update = (key: number, change: Partial<Row>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  const firstValue = (name: string) => {
    const definition = byName.get(name) ?? fields[0];
    return isChoice(definition) ? choiceOptions(definition, config)[0]?.value ?? "" : "";
  };
  function submit() {
    // The native submit handler only serializes; the browser then sends the GET form.
    const items = rows.flatMap((row) => {
      const field = row.field || fields[0].name;
      const definition = byName.get(field);
      const value = definition && isChoice(definition) ? row.value : row.value.trim();
      return definition && value !== "" ? [{ field, op: defaults[definition.type] ?? "contains", value }] : [];
    });
    if (hidden.current) hidden.current.value = JSON.stringify({ logic: "AND", items });
  }
  return (
    <form method="GET" action={action} id="filters-form" className="ms-0 ms-lg-5" data-config-id="filters-config-json"
      data-seccion-filtros-favoritos={favorites.section} data-url-filtros-favoritos={favorites.url}
      data-plantilla-url-filtro-favorito={favorites.detail_url_template} onSubmit={submit}>
      <div id="poncho-filters-rows" className="poncho-rows">
        {rows.map((row, index) => {
          const definition = byName.get(row.field) ?? fields[0];
          const choice = isChoice(definition);
          const options = choice ? choiceOptions(definition, config) : [];
          if (choice && row.value !== "" && !options.some((o) => o.value === row.value)) options.push({ value: row.value, label: row.value });
          return (
            <div key={row.key} className="poncho-search poncho-search--row">
              <select className="poncho-search__field" data-rol="campo" aria-label="Buscar por" value={row.field}
                onChange={(e) => update(row.key, { field: e.target.value, value: firstValue(e.target.value) })}>
                <option value="">Buscar por</option>
                {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
              </select>
              <div className="poncho-search__box">
                <input type="text" className="poncho-search__input" data-rol="valor" autoComplete="off" aria-label="Valor a buscar"
                  placeholder={`Buscar por filtro ${index + 1}`} value={choice ? "" : row.value} hidden={choice} style={{ display: choice ? "none" : "" }}
                  step={definition.input?.step} min={definition.input?.min} max={definition.input?.max}
                  onChange={(e) => update(row.key, { value: e.target.value })} />
                <select className="poncho-search__input poncho-search__input--select" data-rol="valor-select" aria-label="Valor a buscar"
                  hidden={!choice} style={{ display: choice ? "" : "none" }} value={choice ? row.value : ""}
                  onChange={(e) => update(row.key, { value: e.target.value })}>
                  {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
              </div>
              <div className="poncho-row-actions">
                <button type="button" className="poncho-addfilter" data-rol="agregar"
                  onClick={() => setRows((current) => {
                    const field = config.defaultField && byName.has(config.defaultField) ? config.defaultField : "";
                    return [...current, { key: next.current++, field, value: firstValue(field) }];
                  })}>
                  <i className="fas fa-plus" aria-hidden="true" /><span>Filtro</span>
                </button>
                <button type="button" className="poncho-removefilter" data-rol="quitar" hidden={index === 0} style={{ display: index > 0 ? "" : "none" }}
                  onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}>
                  <i className="fas fa-minus" aria-hidden="true" /><span>Filtro</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <input ref={hidden} type="hidden" name="filters" id="filters-input" />
    </form>
  );
}
