/* eslint-disable react-refresh/only-export-components -- shared VAT list pieces export their validators with the components. */
import { useState, type ReactNode } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { Pagination } from "./listControls";
import { internal, record, text } from "./MainFrame";

/**
 * Pieces the VAT listados share (`vat/*_list.html`): the simple `search_bar.html`
 * (field `busqueda`, Resetear and the add button), the card with the sortable table
 * (`listSort.js`, `poncho_scroll_tablas.js`) and `pagination.html`.
 */
export type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type Page = { is_paginated: boolean; number: number; num_pages: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };

const LEVELS = ["success", "error", "warning", "info"];
export const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const bool = (v: unknown): v is boolean => typeof v === "boolean";
export const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
export const pageValid = (p: unknown) => record(p) && bool(p.is_paginated) && integer(p.number) && integer(p.num_pages) && integer(p.count) &&
  (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
  Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_without_page);
export const listUrlsValid = (u: unknown) => record(u) && internal(u.list) && internal(u.create);

/** Full-page actions of the native forms; replaceable in tests. */
export const vatNavigation = { confirm: (message: string) => window.confirm(message), assign: (to: string) => window.location.assign(to) };

/** `components/search_bar.html`, simple mode with the default `busqueda` parameter and an add button. */
export function VatSearchBar({ title, placeholder, query, reset, add }: {
  title: string; placeholder: string; query: string; reset: string; add: { url: string; text: string };
}) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">{title}</h2>
    <form method="GET" action="" id="simple-search-form">
      <div className="poncho-search poncho-search--solo"><div className="poncho-search__box">
        <input type="search" id="ajax-search-input" name="busqueda" className="poncho-search__input" placeholder={placeholder}
          title={placeholder} autoComplete="off" aria-label={placeholder} defaultValue={query} />
        <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
      </div></div>
      <div className="poncho-search__meta"><span id="ajax-results-count" /></div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
    </form>
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={reset} className="poncho-btn poncho-btn--neutro">Resetear</a>
      <a href={add.url} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />{add.text}</a>
    </div></div>
  </>;
}

function parseDateForSort(value: string): number | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? parsed.getTime() : null;
}

/** `listSort.js` comparison: dates, then numbers, then text without case or accents. */
export function compareForSort(a: string, b: string): number {
  const ad = parseDateForSort(a), bd = parseDateForSort(b);
  if (ad !== null && bd !== null) return ad - bd;
  const an = parseFloat(a), bn = parseFloat(b);
  if (!Number.isNaN(an) && !Number.isNaN(bn) && a !== "" && b !== "") return an - bn;
  const plain = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return plain(a).localeCompare(plain(b), "es", { sensitivity: "base" });
}

type Header = { title: string; sortable?: { column: string }; notexport?: boolean };

/**
 * `<div class="row mt-5 max-width-100">` card with the table of a listado. Only the headers marked
 * `sortable` order the rows on the client (three states like `listSort.js`); `value` gives the
 * `data-*` value a row sorts by.
 */
export function VatTable<T extends { id: number }>({ headers, rows, sortValue, renderRow, empty, columns }: {
  headers: Header[]; rows: T[]; sortValue: (row: T, column: string) => string; renderRow: (row: T) => ReactNode;
  empty: { title: string; text: string }; columns: number;
}) {
  const [ordered, setOrdered] = useState(rows);
  const [sort, setSort] = useState<{ column: string | null; direction: "asc" | "desc" | null }>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(rows.length));
  function sortBy(column: string) {
    const direction = sort.column === column ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ column: direction ? column : null, direction });
    setTouched((current) => (current.includes(column) ? current : [...current, column]));
    if (!direction) return;
    setOrdered((current) => [...current].sort((a, b) => {
      const value = compareForSort(sortValue(a, column), sortValue(b, column));
      return direction === "asc" ? value : -value;
    }));
  }
  return (
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card">
      <div ref={cardRef} className={`card-body ${classes.card}`}>
        <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
          <table className="table table-bordered table-striped projects">
            <thead><tr>
              {headers.map((h) => (h.sortable ? (
                <th key={h.title} className={`sortable ${sort.column === h.sortable.column ? `sort-${sort.direction}` : ""}`.trimEnd()} data-column={h.sortable.column}
                  onClick={() => sortBy(h.sortable!.column)}>
                  {h.title}{" "}
                  <i className={sort.column === h.sortable.column ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                    : touched.includes(h.sortable.column) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                </th>
              ) : <th key={h.title} className={h.notexport ? "notexport" : undefined}>{h.title}</th>))}
            </tr></thead>
            <tbody>
              {ordered.length ? ordered.map((row) => renderRow(row)) : (
                <tr><td colSpan={columns}><div className="no-comedores-message"><h3>{empty.title}</h3><p>{empty.text}</p></div></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div></div></div>
  );
}

/** `components/pagination.html` with «Volver»/«Continuar»; an empty page has no count line. */
export function VatPagination({ page, shown }: { page: Page; shown: number }) {
  return <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next} range={page.range}
    href={(n) => `?${page.query_without_page}page=${n}`} count={shown > 0 ? page.count : null} />;
}
