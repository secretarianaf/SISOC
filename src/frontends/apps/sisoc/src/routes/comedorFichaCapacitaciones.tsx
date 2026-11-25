/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the table types, their validation, the review call and the card. */
import { Fragment, useMemo, useState } from "react";
import { internal, record, text, webClient } from "./MainFrame";

/**
 * CO07.01 ficha, «Capacitaciones» (`comedor_detail.html`): the certificates table the native page
 * turns into a DataTables 1.11.5 table (Bootstrap 4 skin, English texts, first column ascending,
 * ten rows per page) and its Aceptar / Rechazar actions. The review POSTs to the web API of the
 * certificate (`revisar`), which runs the native `review_certificate`; the native page `alert()`s
 * the failures and updates the row in place, as this component does.
 */
export type Capacitacion = { id: number; capacitacion: string; estado: string; archivo: string | null; observacion: string; revisar: string };
export type Capacitaciones = { items: Capacitacion[] };

export function capacitacionesValid(v: unknown): v is Capacitaciones | null {
  return v === null || (record(v) && Array.isArray(v.items) && v.items.every((c) => record(c) && Number.isSafeInteger(c.id) && text(c.capacitacion) && text(c.estado) &&
    (c.archivo === null || text(c.archivo)) && text(c.observacion) && internal(c.revisar)));
}

/** The review seam: tests replace `alert`. */
export const capacitacionesDialogs = { alert: (message: string) => window.alert(message) };

const BADGES: Record<string, [string, string]> = {
  aceptado: ["bg-success", "ACEPTADO"], rechazado: ["bg-danger", "RECHAZADO"], presentado: ["bg-warning text-dark", "PRESENTADO"],
};
const badge = (estado: string): [string, string] => BADGES[estado] ?? ["bg-secondary", "SIN PRESENTAR"];
const FINAL = ["sin_presentar", "aceptado", "rechazado"];
const HEADERS = ["Capacitación", "Estado", "Certificado", "Observación", "Acciones"];
const LENGTHS = [10, 25, 50, 100];
const apiPath = (url: string) => url.replace(/^\/api\//, "");

/** What DataTables reads from a row: the text of each cell. */
const cells = (c: Capacitacion) => [c.capacitacion, badge(c.estado)[1], c.archivo ? "Ver archivo" : "-", c.observacion, "Aceptar Rechazar"];

/** DataTables `_numbers` for `simple_numbers` with 7 buttons. */
export function pageNumbers(page: number, pages: number, buttons = 7): (number | "ellipsis")[] {
  const range = (from: number, to: number) => Array.from({ length: Math.max(0, to - from) }, (_, i) => from + i);
  const half = Math.floor(buttons / 2);
  if (buttons > pages) return range(0, pages);
  if (page <= half) return [...range(0, buttons - 2), "ellipsis", pages - 1];
  if (page >= pages - 1 - half) return [0, "ellipsis", ...range(pages - (buttons - 2), pages)];
  return [0, "ellipsis", ...range(page - half + 2, page + half - 1), "ellipsis", pages - 1];
}

async function review(url: string, estado: string, observacion: string): Promise<{ estado: string; observacion: string | null }> {
  const body = new URLSearchParams({ estado });
  if (observacion) body.append("observacion", observacion);
  const { data, status } = await webClient.post(apiPath(url), body, { validateStatus: () => true, headers: { "X-Requested-With": "XMLHttpRequest" } });
  if (status < 200 || status >= 300 || !record(data) || data.success !== true) {
    throw new Error(record(data) && typeof data.error === "string" ? data.error : "No se pudo actualizar el estado.");
  }
  const item = record(data.item) ? data.item : {};
  return { estado: typeof item.estado === "string" ? item.estado : "", observacion: typeof item.observacion === "string" ? item.observacion : null };
}

export function CapacitacionesCard({ data }: { data: Capacitaciones }) {
  const [items, setItems] = useState(data.items);
  const [order, setOrder] = useState<{ column: number; dir: "asc" | "desc" }>({ column: 0, dir: "asc" });
  const [search, setSearch] = useState("");
  const [length, setLength] = useState(10);
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  const rows = useMemo(() => {
    const words = search.toLowerCase().split(/\s+/).filter(Boolean);
    const withIndex = items.map((c, index) => ({ c, index, text: cells(c) }));
    const filtered = withIndex.filter((r) => words.every((w) => r.text.join(" ").toLowerCase().includes(w)));
    // DataTables sorts strings in lower case and breaks ties with the original position.
    return filtered.sort((a, b) => {
      const x = a.text[order.column].toLowerCase(), y = b.text[order.column].toLowerCase();
      const cmp = x < y ? -1 : x > y ? 1 : 0;
      return (order.dir === "asc" ? cmp : -cmp) || a.index - b.index;
    });
  }, [items, search, order]);

  const pages = Math.max(1, Math.ceil(rows.length / length));
  const current = Math.min(page, pages - 1);
  const start = current * length;
  const visible = rows.slice(start, start + length);

  function sortBy(column: number) {
    setOrder((o) => (o.column === column ? { column, dir: o.dir === "asc" ? "desc" : "asc" } : { column, dir: "asc" }));
    setPage(0);
  }

  async function update(id: number, url: string, estado: string, observacion: string, failure: string) {
    try {
      const item = await review(url, estado, observacion);
      setItems((all) => all.map((c) => (c.id === id ? { ...c, estado: item.estado, observacion: item.observacion || "-" } : c)));
      setEditing((e) => (e === id ? null : e));
    } catch (error) {
      capacitacionesDialogs.alert(error instanceof Error && error.message ? error.message : failure);
    }
  }

  function confirmReject(c: Capacitacion) {
    const observacion = draft.trim();
    if (!observacion) { capacitacionesDialogs.alert("Debe ingresar una observación para rechazar."); return; }
    void update(c.id, c.revisar, "rechazado", observacion, "No se pudo rechazar el certificado.");
  }

  const nth = (column: number) => (order.column === column ? (order.dir === "asc" ? "sorting_asc" : "sorting_desc") : "sorting");
  const info = rows.length
    ? `Showing ${start + 1} to ${Math.min(start + length, rows.length)} of ${rows.length} entries${rows.length !== items.length ? ` (filtered from ${items.length} total entries)` : ""}`
    : `Showing 0 to 0 of 0 entries${items.length ? ` (filtered from ${items.length} total entries)` : ""}`;

  return (
    <div className="row mb-3">
      <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap4.min.css" />
      <div className="col-12">
        <div className="card bg-card">
          <div className="card-header py-2 d-flex justify-content-between align-items-center"><h4 className="fw-bold my-1">Capacitaciones</h4></div>
          <div className="card-body">
            <div className="table-responsive-lg">
              <div id="capacitacionesTable_wrapper" className="dataTables_wrapper dt-bootstrap4">
                <div className="row">
                  <div className="col-sm-12 col-md-6">
                    <div className="dataTables_length" id="capacitacionesTable_length">
                      <label>Show{" "}
                        <select name="capacitacionesTable_length" aria-controls="capacitacionesTable" className="custom-select custom-select-sm form-control form-control-sm" value={length} onChange={(e) => { setLength(Number(e.target.value)); setPage(0); }}>
                          {LENGTHS.map((n) => <option key={n} value={n}>{n}</option>)}
                        </select>{" "}entries
                      </label>
                    </div>
                  </div>
                  <div className="col-sm-12 col-md-6">
                    <div id="capacitacionesTable_filter" className="dataTables_filter">
                      <label>Search:<input type="search" className="form-control form-control-sm" placeholder="" aria-controls="capacitacionesTable" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} /></label>
                    </div>
                  </div>
                </div>
                <div className="row">
                  <div className="col-sm-12">
                    <table className="table table-bordered table-striped projects table-hover align-middle dataTable no-footer" id="capacitacionesTable" role="grid" aria-describedby="capacitacionesTable_info">
                      <thead>
                        <tr role="row">
                          {HEADERS.map((h, i) => (
                            <th key={h} className={nth(i)} tabIndex={0} aria-controls="capacitacionesTable" rowSpan={1} colSpan={1}
                              aria-sort={order.column === i ? (order.dir === "asc" ? "ascending" : "descending") : undefined}
                              aria-label={`${h}: activate to sort column ${order.column === i && order.dir === "asc" ? "descending" : "ascending"}`}
                              onClick={() => sortBy(i)} onKeyDown={(e) => { if (e.key === "Enter") sortBy(i); }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {visible.length ? visible.map(({ c }, position) => {
                          const [cls, label] = badge(c.estado);
                          const disabled = FINAL.includes(c.estado);
                          return (
                            <Fragment key={c.id}>
                              <tr data-cert-id={c.id} role="row" className={position % 2 ? "even" : "odd"}>
                                <td>{c.capacitacion}</td>
                                <td className="cert-estado"><span className={`badge ${cls}`}>{label}</span></td>
                                <td className="cert-archivo">{c.archivo ? <a href={c.archivo} target="_blank" rel="noreferrer">Ver archivo</a> : "-"}</td>
                                <td className="cert-observacion">{c.observacion}</td>
                                <td>
                                  <div className="d-flex flex-wrap gap-1">
                                    <button type="button" className="btn btn-sm btn-success cert-accept-btn" disabled={disabled}
                                      onClick={() => { setEditing(null); void update(c.id, c.revisar, "aceptado", "", "No se pudo aceptar el certificado."); }}>Aceptar</button>
                                    <button type="button" className="btn btn-sm btn-danger cert-reject-btn" disabled={disabled}
                                      onClick={() => { if (editing === c.id) { setEditing(null); } else { setDraft(""); setEditing(c.id); } }}>Rechazar</button>
                                  </div>
                                </td>
                              </tr>
                              {editing === c.id && (
                                <tr>
                                  <td colSpan={5}>
                                    <div className="cert-reject-editor py-2">
                                      <textarea id={`cert-reject-text-${c.id}`} className="form-control cert-reject-text" rows={2} placeholder="Ingrese una observacion" value={draft} onChange={(e) => setDraft(e.target.value)} />
                                      <div className="d-flex justify-content-end gap-2 mt-2">
                                        <button type="button" className="btn btn-sm btn-outline-secondary cert-reject-cancel-btn" onClick={() => setEditing(null)}>Cancelar</button>
                                        <button type="button" className="btn btn-sm btn-danger cert-reject-confirm-btn" onClick={() => confirmReject(c)}>Aceptar</button>
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </Fragment>
                          );
                        }) : <tr className="odd"><td valign="top" colSpan={5} className="dataTables_empty">{items.length ? "No matching records found" : "No data available in table"}</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="row">
                  <div className="col-sm-12 col-md-5"><div className="dataTables_info" id="capacitacionesTable_info" role="status" aria-live="polite">{info}</div></div>
                  <div className="col-sm-12 col-md-7">
                    <div className="dataTables_paginate paging_simple_numbers" id="capacitacionesTable_paginate">
                      <ul className="pagination">
                        <li className={`paginate_button page-item previous${current === 0 ? " disabled" : ""}`} id="capacitacionesTable_previous">
                          <a href="#" aria-controls="capacitacionesTable" data-dt-idx="previous" tabIndex={0} className="page-link" onClick={(e) => { e.preventDefault(); if (current > 0) setPage(current - 1); }}>Previous</a>
                        </li>
                        {pageNumbers(current, pages).map((n, i) => (n === "ellipsis"
                          ? <li key={`e${i}`} className="paginate_button page-item disabled" id="capacitacionesTable_ellipsis"><a href="#" aria-controls="capacitacionesTable" tabIndex={0} className="page-link" onClick={(e) => e.preventDefault()}>…</a></li>
                          : <li key={n} className={`paginate_button page-item${n === current ? " active" : ""}`}><a href="#" aria-controls="capacitacionesTable" data-dt-idx={n} tabIndex={0} className="page-link" onClick={(e) => { e.preventDefault(); setPage(n); }}>{n + 1}</a></li>))}
                        <li className={`paginate_button page-item next${current >= pages - 1 ? " disabled" : ""}`} id="capacitacionesTable_next">
                          <a href="#" aria-controls="capacitacionesTable" data-dt-idx="next" tabIndex={0} className="page-link" onClick={(e) => { e.preventDefault(); if (current < pages - 1) setPage(current + 1); }}>Next</a>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
