/* eslint-disable react-refresh/only-export-components -- shared V06.01 pieces: hook, breadcrumb and error markup travel together. */
import { useRef, useState, type FormEvent } from "react";
import { Breadcrumb, postForm } from "./MainFrame";
import { UNCERTAIN, type Field } from "./vatFormShared";
import { vatNavigation } from "./vatShared";

/**
 * Pieces the V06.01 pages (centros list, contactos, identificadores, ubicaciones, modalidades) share:
 * the POST that deletes a record through its native view, the `{{ field.errors }}` markup and the breadcrumb.
 */

/** POST of a native delete: `{ok, redirect}` navigates, 403 is the access screen, anything else is uncertain. */
export function usePostDelete(endpoint: string, forbidden: (d: unknown) => void, confirmText?: string) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    if (confirmText && !vatNavigation.confirm(confirmText)) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  return { uncertain, submit: (e: FormEvent) => void submit(e) };
}

export const UncertainNotice = ({ show }: { show: boolean }) => (show ? <p role="alert">{UNCERTAIN}</p> : null);

/** `<small class="text-danger">{{ field.errors }}</small>`: Django prints the errors as an `errorlist`. */
export const FieldErrors = ({ f }: { f: Field }) => (f.errors.length
  ? <small className="text-danger"><ul className="errorlist">{f.errors.map((e) => <li key={e}>{e}</li>)}</ul></small> : null);

export const vatBreadcrumb = (items: { text: string; url: string | null }[]) => <Breadcrumb items={items} />;
