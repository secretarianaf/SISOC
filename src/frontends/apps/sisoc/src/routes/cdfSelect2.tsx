import Select2, { type Choice } from "./select2";

/**
 * `actividad_preferida` of `beneficiarios_form.html`: the markup of the native
 * Select2 4.1 multiple (`centro_familia_beneficiarios.js`: width 100%, the
 * `data-placeholder` of the widget). The hidden `<select>` keeps the crispy
 * classes of this form. Options of the shared `Select2` (see `select2.tsx`).
 */
export type { Choice };

export default function CdfSelect2({ id, name, placeholder, className, choices, value, onChange, invalid, describedBy }: {
  id: string;
  name: string;
  placeholder: string;
  className: string;
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  invalid: boolean;
  describedBy: string;
}) {
  return <Select2 id={id} name={name} multiple placeholder={placeholder} selectClassName={className} invalid={invalid}
    selectProps={{ "data-placeholder": placeholder, required: true, "aria-describedby": describedBy || undefined }}
    choices={choices} value={value} onChange={onChange} noResults="No results found" clearTrigger="click" focusMarker="search"
    termHandling="keep" enterOnSelected="close" removeOpensResults outsideClick="results" />;
}
