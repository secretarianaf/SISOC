import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export type SelectOption = { value: string; label: string };

/** Accent- and case-insensitive text, like the select2 matcher of the native page. */
const normalize = (text: string) => text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

/**
 * Native `<select>` with a search box that narrows its options, replacing the
 * select2 widgets of the native template. The selected option always stays
 * listed so filtering never changes the value silently; Enter in the search
 * box picks the first match and moves focus to the list.
 */
export function SearchableSelect({ label, searchLabel, name, options, value, defaultValue, onChange, required, placeholder }: {
  label: ReactNode; searchLabel?: string; name: string; options: SelectOption[]; value?: string; defaultValue?: string;
  onChange?: (value: string) => void; required?: boolean; placeholder?: string;
}) {
  const id = useId();
  const selectRef = useRef<HTMLSelectElement>(null);
  const [term, setTerm] = useState("");
  const [own, setOwn] = useState(defaultValue ?? (placeholder === undefined ? options[0]?.value ?? "" : ""));
  const current = value ?? own;
  const needle = normalize(term.trim());
  const matches = needle ? options.filter((o) => normalize(o.label).includes(needle)) : options;
  const visible = needle ? options.filter((o) => o.value === current || matches.includes(o)) : options;
  const plain = typeof label === "string" ? label.replace(/[\s*:]+$/, "") : name;
  const choose = (next: string) => { if (value === undefined) setOwn(next); onChange?.(next); };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (matches[0]) choose(matches[0].value);
    selectRef.current?.focus();
  };
  return <div className="ed-search-select">
    <label htmlFor={id}>{label}</label>
    <input type="search" aria-label={searchLabel ?? `Buscar ${plain}`} aria-controls={id} placeholder="Buscar…" value={term} onChange={(e) => setTerm(e.target.value)} onKeyDown={onKeyDown} />
    <select id={id} ref={selectRef} name={name} required={required} value={current} onChange={(e) => choose(e.target.value)}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {visible.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
    {needle && <small role="status" aria-live="polite">{matches.length === 1 ? "1 coincidencia" : `${matches.length} coincidencias`}</small>}
  </div>;
}
