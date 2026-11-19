/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { prerequisiteFromForbidden } from "../webAccess";
import { Breadcrumb, breadcrumbValid, record, renderMain, text, useMainResource, webClient, type Breadcrumbs } from "./MainFrame";
import { ModuleHeader, PAS_API, PAS_STYLESHEET, integer, list, shape } from "./pasFrame";
import type { RouteDefinition } from "./types";

/**
 * PAS import of titulares on the native URL `pas/titulares/importar`
 * (`pas/titulares_import.html`). The page reads `/api/web/pas/titulares/importar/`
 * and posts the CSV (multipart `archivo`) to the same endpoint. As the native
 * page, a post shows the result summary with a fresh form, or the form errors;
 * either way the page is back at the top with no focus. The import is synchronous and
 * atomic: it is never retried, a result that cannot be confirmed is reported.
 */
export type ImportData = { breadcrumb: Breadcrumbs; archivo: { label: string; accept: string } };
type Resultado = { total: number; creados: number; duplicados: number; errores: string[] };
type Errors = string[];

export const importValid = (v: unknown): v is ImportData => shape(v, {
  breadcrumb: breadcrumbValid, archivo: (a) => shape(a, { label: text, accept: text }),
});
const resultadoValid = (v: unknown): v is Resultado => shape(v, { total: integer, creados: integer, duplicados: integer, errores: list(text) });

const ENDPOINT = `${PAS_API}titulares/importar/`;
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type Outcome =
  | { kind: "done"; resultado: Resultado }
  | { kind: "invalid"; errors: Errors }
  | { kind: "forbidden"; data: unknown }
  | { kind: "uncertain" };

async function importar(file: File): Promise<Outcome> {
  const body = new FormData();
  body.append("archivo", file);
  try {
    const { data, status } = await webClient.post(ENDPOINT, body, { validateStatus: () => true });
    if (status === 403) return { kind: "forbidden", data };
    if (status === 200 && record(data) && resultadoValid(data.resultado)) return { kind: "done", resultado: data.resultado };
    if (status === 400 && record(data) && record(data.errors) && Array.isArray(data.errors.archivo) && data.errors.archivo.every(text)) {
      return { kind: "invalid", errors: data.errors.archivo };
    }
  } catch {
    // Reported as unconfirmed below.
  }
  return { kind: "uncertain" };
}

function Summary({ resultado }: { resultado: Resultado }) {
  return <>
    <div className="alert alert-info mt-4" role="status">
      Procesados: {resultado.total} · Nuevos: {resultado.creados} · Duplicados omitidos: {resultado.duplicados} · Errores: {resultado.errores.length}
    </div>
    {resultado.errores.length > 0 && <ul className="alert alert-warning">
      {resultado.errores.map((error, i) => <li key={i}>{error}</li>)}
    </ul>}
  </>;
}

function ImportForm({ data, onForbidden }: { data: ImportData; onForbidden: (body: unknown) => void }) {
  const [generation, setGeneration] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [errors, setErrors] = useState<Errors>([]);
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  const input = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const file = input.current?.files?.[0];
    if (!file || working.current) return;
    working.current = true;
    setBusy(true);
    const outcome = await importar(file);
    working.current = false;
    setBusy(false);
    if (outcome.kind === "forbidden") {
      onForbidden(outcome.data);
      return;
    }
    setResultado(outcome.kind === "done" ? outcome.resultado : null);
    setErrors(outcome.kind === "invalid" ? outcome.errors : []);
    setUncertain(outcome.kind === "uncertain");
    // The native page reloads with an empty file field; a rejection starts at the top.
    setGeneration((n) => n + 1);
    window.scrollTo(0, 0);
    // Focus starts over at the top of the document, as after the native reload.
    document.body.setAttribute("tabindex", "-1");
    document.body.focus({ preventScroll: true });
    document.body.removeAttribute("tabindex");
  }

  return <>
    <form method="post" encType="multipart/form-data" className="mt-4" onSubmit={(event) => void submit(event)}>
      <div className="mb-3">
        <label htmlFor="id_archivo" className="form-label">{data.archivo.label}</label>{" "}
        <input key={generation} ref={input} type="file" name="archivo" accept={data.archivo.accept} className="form-control" required id="id_archivo" />
        {errors.map((error, i) => <div key={i} className="text-danger mt-2">{error}</div>)}
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        <i className="bi bi-file-earmark-arrow-up" aria-hidden="true" />{" "}
        Importar titulares
      </button>
    </form>
    {uncertain && <div className="alert alert-danger mt-4" role="alert">{UNCERTAIN}</div>}
    {resultado && <Summary resultado={resultado} />}
  </>;
}

function ImportPage() {
  const [state, setState] = useMainResource<ImportData>(ENDPOINT, importValid);
  return renderMain(state, "Cargando importación…", (data) => ({
    title: "Importar titulares PAS",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <>
      {PAS_STYLESHEET}
      <main className="pas-workspace">
        <ModuleHeader title="Importar titulares" />
        <section className="pas-search-panel">
          <div className="pas-section-heading">
            <div>
              <span className="pas-eyebrow">Carga incremental</span>
              <h2>Archivo CSV</h2>
            </div>
          </div>
          <p>
            Columnas obligatorias: <strong>Apellidos/Apellido, Nombres/Nombre, DNI, CUIT, Provincia y Municipio</strong>.
            También se pueden informar Género, Calle, Altura, Email, UltimoEstadoPas y AvisoLiquidacion.
            Calle y Altura forman el domicilio; los campos opcionales vacíos quedan sin dato.
            Género admite M, F o X y también puede encabezarse como ciudadano_genero o ciudadano_genero_cod.
            Los registros cuyo DNI o CUIT ya exista se omiten sin modificar el padrón.
            Los nuevos titulares reciben un IdPersona interno y un token DDJJ vigente. Si no se informa
            UltimoEstadoPas, se asigna el estado Activo.
          </p>
          <ImportForm data={data} onForbidden={(body) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(body) })} />
        </section>
      </main>
    </>,
  }));
}

export const pasTitularesImportarRoute: RouteDefinition<{ page: "titulares-importar" }> = {
  name: "pas-titulares-importar",
  match: (pathname) => (pathname === "/pas/titulares/importar" ? { page: "titulares-importar" } : null),
  render: () => <ImportPage />,
};
