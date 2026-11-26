/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and validator live here with the route. */
import { useRef, useState, type FormEvent, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { sameOriginTarget } from "./cdiObservaciones";
import { client, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI nomina attendance (`centrodeinfancia/nomina_asistencia.html`): the day's attendance of the active
 * nomina, with the native inline scripts (client-side pages of 10, radio toggle-off, "Marcar todos",
 * live counters and the month calendar dialog). The native view stays the authority through
 * `/api/web/cdi/`: the GET sends the rows and the POST saves them (a confirmed one navigates to the native
 * redirect, which carries the flash message); the calendar calls the native JSON endpoint as the native script does.
 */
type Fila = { id: number; nombre: string; dni: string; sala: string; presente: boolean | null; observaciones: string };
type Totales = { presentes: number; ausentes: number; sin_marcar: number };
export type AsistenciaData = {
  centro: { id: number; nombre: string };
  fecha: string;
  fecha_label: string;
  rows: Fila[];
  totals: Totales;
  messages: CdiMessage[];
};

const count = (v: unknown) => Number.isSafeInteger(v) && (v as number) >= 0;

export function asistenciaValid(v: unknown): v is AsistenciaData {
  if (!record(v) || !record(v.centro) || !record(v.totals)) return false;
  return Number.isSafeInteger(v.centro.id) && text(v.centro.nombre) && text(v.fecha) && /^\d{4}-\d{2}-\d{2}$/.test(v.fecha) && text(v.fecha_label) &&
    count(v.totals.presentes) && count(v.totals.ausentes) && count(v.totals.sin_marcar) && messagesValid(v.messages) &&
    Array.isArray(v.rows) && v.rows.every((r) => record(r) && Number.isSafeInteger(r.id) && text(r.nombre) && text(r.dni) && text(r.sala) &&
      (r.presente === null || typeof r.presente === "boolean") && text(r.observaciones));
}

type PostResult = { kind: "redirect"; to: string } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST once, URL-encoded like the native form; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: URLSearchParams): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 403 });
    if (status === 403) return { kind: "forbidden", data };
    const to = record(data) && data.ok === true ? sameOriginTarget(data.redirect) : null;
    return to ? { kind: "redirect", to } : { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const PAGE_SIZE = 10;
const pad = (n: number) => String(n).padStart(2, "0");
const iso = (year: number, month: number, day: number) => `${year}-${pad(month + 1)}-${pad(day)}`;

type Shown = { visible: Date; marked: Record<string, boolean> };

/** The native script's month dialog state: it fetches the days with attendance of the shown month from the native JSON endpoint. */
function useCalendario(centro: number, initial: string) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(initial);
  const [shown, setShown] = useState<Shown | null>(null);
  const visible = useRef(new Date(`${initial}T00:00:00`));
  const latest = useRef(0);

  async function loadMonth() {
    const ticket = ++latest.current;
    const year = visible.current.getFullYear();
    const month = visible.current.getMonth();
    let dias: unknown[] = [];
    try {
      const response = await fetch(`/centrodeinfancia/${centro}/nomina/asistencia/calendario/?mes=${year}-${pad(month + 1)}`, { credentials: "same-origin" });
      const data: unknown = response.ok ? await response.json() : null;
      if (record(data) && Array.isArray(data.dias)) dias = data.dias;
    } catch {
      dias = [];
    }
    if (ticket !== latest.current) return;
    setShown({ visible: new Date(visible.current), marked: Object.fromEntries(dias.filter(text).map((d) => [d, true])) });
  }
  function openDialog() {
    visible.current = new Date(`${selected}T00:00:00`);
    setOpen(true);
    void loadMonth();
  }
  function shift(delta: number) {
    const next = new Date(visible.current);
    next.setMonth(next.getMonth() + delta);
    visible.current = next;
    void loadMonth();
  }
  return { open, selected, shown, setSelected, openDialog, shift, hide: () => setOpen(false) };
}

type Calendar = ReturnType<typeof useCalendario>;

function Calendario({ calendar, close }: { calendar: Calendar; close: () => void }) {
  const { open, selected, shown, setSelected, shift } = calendar;
  const year = shown?.visible.getFullYear() ?? 0;
  const month = shown?.visible.getMonth() ?? 0;
  const firstWeekday = shown ? (new Date(year, month, 1).getDay() + 6) % 7 : 0;
  const totalDays = shown ? new Date(year, month + 1, 0).getDate() : 0;
  return (
    <div id="asisCalendarDialog" className="asis-calendar-backdrop" hidden={!open} role="dialog" aria-modal="true" aria-labelledby="asisCalendarMonth"
      onKeyDown={(event: KeyboardEvent<HTMLDivElement>) => { if (event.key === "Escape") close(); }}>
      <div className="asis-calendar-panel">
        <div className="asis-calendar-header">
          <button type="button" className="cdf-btn" id="asisCalendarPrev" aria-label="Mes anterior" onClick={() => shift(-1)}>
            <i className="bi bi-chevron-left" />
          </button>
          <strong id="asisCalendarMonth">{shown ? shown.visible.toLocaleDateString("es-AR", { month: "long", year: "numeric" }) : ""}</strong>
          <button type="button" className="cdf-btn" id="asisCalendarNext" aria-label="Mes siguiente" onClick={() => shift(1)}>
            <i className="bi bi-chevron-right" />
          </button>
        </div>
        <div className="asis-calendar-week" aria-hidden="true">
          <span>Lun</span><span>Mar</span><span>Mié</span><span>Jue</span><span>Vie</span><span>Sáb</span><span>Dom</span>
        </div>
        <div id="asisCalendarDays" className="asis-calendar-days" role="grid">
          {shown && Array.from({ length: firstWeekday }, (_, n) => <span key={`blank-${n}`} />)}
          {shown && Array.from({ length: totalDays }, (_, n) => {
            const day = n + 1;
            const value = iso(year, month, day);
            const marked = shown.marked[value];
            return (
              <button key={value} type="button" className={`asis-calendar-day${value === selected ? " is-selected" : ""}${marked ? " has-attendance" : ""}`}
                aria-label={value + (marked ? ", con asistencia registrada" : "")} onClick={() => setSelected(value)}>{day}</button>
            );
          })}
        </div>
        <div className="asis-calendar-actions">
          <button type="button" className="cdf-btn" id="asisCalendarCancel" onClick={close}>Cancelar</button>
          <button type="button" className="cdf-btn cdf-btn--primary" id="asisCalendarApply" onClick={() => navigation.assign(`?fecha=${encodeURIComponent(selected)}`)}>Aplicar</button>
        </div>
      </div>
    </div>
  );
}

function AsistenciaContent({ data }: { data: AsistenciaData }) {
  const [totals, setTotals] = useState(data.totals);
  const [page, setPage] = useState(1);
  const calendar = useCalendario(data.centro.id, data.fecha);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const busy = useRef(false);
  const body = useRef<HTMLTableSectionElement>(null);
  const allPresent = useRef<HTMLInputElement>(null);
  const allAbsent = useRef<HTMLInputElement>(null);
  const openButton = useRef<HTMLButtonElement>(null);
  const previous = useRef<HTMLInputElement | null>(null);
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;

  const rowsOf = () => Array.from(body.current?.querySelectorAll<HTMLTableRowElement>(".asis-row") ?? []);
  const totalPages = Math.max(1, Math.ceil(data.rows.length / PAGE_SIZE));
  const current = Math.min(Math.max(page, 1), totalPages);
  const start = (current - 1) * PAGE_SIZE;

  const inputOf = (target: EventTarget) => {
    const element = target as Element;
    if (element.matches(".asis-present, .asis-absent")) return element as HTMLInputElement;
    return element.closest("label.cdf-mark")?.querySelector<HTMLInputElement>(".asis-present, .asis-absent") ?? null;
  };
  function recount() {
    let presentes = 0, ausentes = 0, sinMarcar = 0;
    rowsOf().forEach((row) => {
      if (row.querySelector<HTMLInputElement>(".asis-present")?.checked) presentes += 1;
      else if (row.querySelector<HTMLInputElement>(".asis-absent")?.checked) ausentes += 1;
      else sinMarcar += 1;
    });
    setTotals({ presentes, ausentes, sin_marcar: sinMarcar });
  }
  function setAll(selector: string, checked: boolean) {
    rowsOf().forEach((row) => {
      const input = row.querySelector<HTMLInputElement>(selector);
      if (!input) return;
      if (checked) input.checked = true;
      else if (input.checked) input.checked = false;
    });
    recount();
  }
  const onPointerDown = (event: PointerEvent) => {
    const input = inputOf(event.target);
    previous.current = input && input.checked ? input : null;
  };
  const onClick = (event: MouseEvent) => {
    const input = inputOf(event.target);
    if (input && input === previous.current) {
      event.preventDefault();
      input.checked = false;
      recount();
    }
    previous.current = null;
  };
  const onKeyDown = (event: KeyboardEvent) => {
    const input = inputOf(event.target);
    if (input && input.checked && event.key === " ") {
      event.preventDefault();
      input.checked = false;
      recount();
    }
  };
  function closeCalendar() {
    calendar.hide();
    openButton.current?.focus();
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    const form = new URLSearchParams();
    new FormData(event.currentTarget).forEach((value, key) => { if (typeof value === "string") form.append(key, value); });
    const result = await postOnce(`web/cdi/centros/${data.centro.id}/nomina/asistencia/`, form);
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else setUncertain(true);
    busy.current = false;
    setPending(false);
  }

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <link rel="stylesheet" href="/static/custom/css/centrodeinfancia.css" />
      <div className="cdf-page cdi-page">
        <div className="container-fluid">
          <div className="cdf-hero">
            <div className="cdf-hero-block">
              <p className="cdi-hero-kicker">Nómina del centro · Asistencia</p>
              <h1>{data.centro.nombre}</h1>
            </div>
            <div className="cdf-hero-side">
              <span className="cdf-pill cdf-pill--gold">{data.fecha_label}</span>
            </div>
          </div>

          <div className="cdf-card">
            <div className="cdf-card-head">
              <i className="bi bi-calendar3" />{" "}
              <span>Fecha de asistencia</span>
            </div>
            <div className="cdf-card-body">
              <button type="button" className="cdf-btn cdf-btn--primary" id="asisCalendarOpen" ref={openButton} aria-haspopup="dialog" aria-controls="asisCalendarDialog"
                onClick={calendar.openDialog}>
                <i className="bi bi-calendar3" />{" "}
                <span id="asisCalendarLabel">{data.fecha_label}</span>
              </button>
            </div>
          </div>

          <div className="cdi-stats-row">
            <div className="cdi-stat-card">
              <span className="cdi-stat-dot" style={{ background: "var(--cdf-green)" }} />
              <div>
                <div className="cdi-stat-num" id="asisMetricPresentes">{totals.presentes}</div>
                <div className="cdi-stat-lbl">Presentes</div>
              </div>
            </div>
            <div className="cdi-stat-card">
              <span className="cdi-stat-dot" style={{ background: "var(--cdf-red)" }} />
              <div>
                <div className="cdi-stat-num" id="asisMetricAusentes">{totals.ausentes}</div>
                <div className="cdi-stat-lbl">Ausentes</div>
              </div>
            </div>
            <div className="cdi-stat-card">
              <span className="cdi-stat-dot cdi-stat-dot--gold" />
              <div>
                <div className="cdi-stat-num" id="asisMetricSinMarcar">{totals.sin_marcar}</div>
                <div className="cdi-stat-lbl">Sin marcar</div>
              </div>
            </div>
          </div>

          {data.rows.length ? (
            <form method="post" id="asisForm" onSubmit={submit}>
              <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
              <input type="hidden" name="fecha" value={data.fecha} />
              <div className="cdf-card" id="asisTabla">
                <div className="cdf-card-head">
                  <i className="bi bi-people" />{" "}
                  <span>Registro de asistencia — {data.fecha_label}</span>
                </div>
                <div className="cdf-tbl-scroll">
                  <table className="cdf-table">
                    <thead>
                      <tr>
                        <th>Apellido y nombre</th>
                        <th>DNI</th>
                        <th>Sala</th>
                        <th>
                          <label className="cdf-mark">
                            <input type="checkbox" className="cdf-check cdf-check--present" id="asisMarcarPresentes" ref={allPresent}
                              onChange={(e) => { if (e.currentTarget.checked && allAbsent.current) allAbsent.current.checked = false; setAll(".asis-present", e.currentTarget.checked); }} />{" "}
                            Marcar todos
                          </label>
                        </th>
                        <th>
                          <label className="cdf-mark">
                            <input type="checkbox" className="cdf-check cdf-check--absent" id="asisMarcarAusentes" ref={allAbsent}
                              onChange={(e) => { if (e.currentTarget.checked && allPresent.current) allPresent.current.checked = false; setAll(".asis-absent", e.currentTarget.checked); }} />{" "}
                            Marcar todos
                          </label>
                        </th>
                        <th>Observaciones</th>
                      </tr>
                    </thead>
                    <tbody id="asisTablaBody" ref={body} onPointerDown={onPointerDown} onClick={onClick} onKeyDown={onKeyDown} onChange={recount}>
                      {data.rows.map((fila, index) => (
                        <tr key={fila.id} className={`asis-row${index < start || index >= start + PAGE_SIZE ? " d-none" : ""}`}>
                          <td>{fila.nombre}</td>
                          <td>{fila.dni}</td>
                          <td>{fila.sala}</td>
                          <td>
                            <label className="cdf-mark">
                              <input type="radio" className="cdf-check cdf-check--present asis-present" name={`presente_${fila.id}`} value="1" defaultChecked={fila.presente === true} />{" "}
                              Presente
                            </label>
                          </td>
                          <td>
                            <label className="cdf-mark">
                              <input type="radio" className="cdf-check cdf-check--absent asis-absent" name={`presente_${fila.id}`} value="0" defaultChecked={fila.presente === false} />{" "}
                              Ausente
                            </label>
                          </td>
                          <td>
                            <input type="text" name={`obs_${fila.id}`} defaultValue={fila.observaciones} className="cdf-input" aria-label={`Observaciones para ${fila.nombre}`} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="cdf-card-foot justify-content-between">
                  <span className="cdf-td-muted" id="asisConteo">
                    {`Mostrando ${data.rows.length ? start + 1 : 0}-${Math.min(start + PAGE_SIZE, data.rows.length)} de ${data.rows.length}`}
                  </span>
                  <div className="pager">
                    <button type="button" className="cdf-btn" id="asisPrev" aria-label="Página anterior" disabled={current === 1} onClick={() => setPage(current - 1)}>
                      <i className="bi bi-chevron-left" />
                    </button>{" "}
                    <span className="cdf-td-muted" id="asisPager">{`${current} de ${totalPages}`}</span>{" "}
                    <button type="button" className="cdf-btn" id="asisNext" aria-label="Página siguiente" disabled={current === totalPages} onClick={() => setPage(current + 1)}>
                      <i className="bi bi-chevron-right" />
                    </button>
                  </div>
                </div>
              </div>
              <div className="d-flex justify-content-end mt-3">
                <button type="submit" className="cdf-btn cdf-btn--success" disabled={pending || uncertain}>
                  <i className="bi bi-check-lg" />Guardar asistencia
                </button>
              </div>
              {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
            </form>
          ) : (
            <div className="cdf-card">
              <div className="cdf-card-head">
                <i className="bi bi-people" /><span>Registro de asistencia</span>
              </div>
              <div className="cdf-empty">
                <i className="bi bi-person-plus" />
                <p className="cdf-empty-t">Sin nómina activa</p>
                <p className="cdf-empty-s">Agregá personas activas a la nómina para poder tomar asistencia.</p>
              </div>
            </div>
          )}
        </div>
      </div>
      <Calendario calendar={calendar} close={closeCalendar} />
    </>
  );
}

function AsistenciaPage({ centro }: { centro: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/nomina/asistencia/${window.location.search}`, asistenciaValid);
  return renderCdi(state, (data) => ({
    title: `Asistencia de nómina — ${data.centro.nombre}`,
    heading: "",
    appHeader: <></>,
    bodyToasts: true,
    content: <AsistenciaContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/asistencia\/$/;

// Native URL of the CDI nomina attendance; same trailing slash. The calendar endpoint and the
// `trabajadores/asistencia/` redirect are not pages and stay native.
export const cdiNominaAsistenciaRoute: RouteDefinition<{ centro: string }> = {
  name: "cdi-nomina-asistencia",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1] } : null;
  },
  render: ({ centro }) => <AsistenciaPage centro={centro} />,
};
