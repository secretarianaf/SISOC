import { Autocomplete, Checkbox, FormControlLabel, MenuItem, TextField } from "@mui/material";
import { useState } from "react";
import { inetGet, type InetField, type InetOptionsPage } from "@sisoc/api";
import { useInfiniteQuery } from "@tanstack/react-query";
import { queryString } from "./data";

export function Field({ field, value, onChange, optionsPath, values, error, onOptionLabel, placeholder }: {
  field: InetField; value: unknown; onChange: (value: unknown) => void;
  onOptionLabel?: (label: string) => void; optionsPath?: string; values: Record<string, unknown>; error?: string; placeholder?: string;
}) {
  const [search, setSearch] = useState("");
  const dependencies: Record<string, string[]> = {
    municipio: ["provincia"], departamento: ["provincia"],
    localidad: ["provincia", "municipio", "departamento"], subsector: ["sector"],
  };
  const context = Object.fromEntries(Object.entries(values).filter(([name]) =>
    [...["centro", "curso", "comision", "comision_curso"], ...(dependencies[field.name] ?? [])].includes(name) && name !== field.name));
  const params = queryString({ ...context, search, page_size: 50 });
  const remote = useInfiniteQuery({ queryKey: ["inet", "options", optionsPath, field.name, params],
    queryFn: ({ pageParam }) => inetGet<InetOptionsPage>(`${optionsPath}${field.name}/?${params}&page=${pageParam}`),
    initialPageParam: 1, getNextPageParam: (last, _pages, page) => last.next ? page + 1 : undefined,
    enabled: !!optionsPath && field.remote_options && !field.disabled,
  });
  if (field.kind === "checkbox") return <FormControlLabel
    control={<Checkbox checked={!!value} disabled={field.disabled} onChange={(_, checked) => onChange(checked)} />}
    label={field.label} />;
  if (field.remote_options) {
    const options = [...field.options, ...(remote.data?.pages.flatMap((page) => page.results) ?? [])].filter((option, index, rows) => rows.findIndex((item) => item.value === option.value) === index);
    const multiple = field.kind === "multiselect";
    const selected = multiple ? options.filter((option) => Array.isArray(value) && value.includes(option.value)) : options.find((option) => option.value === String(value ?? "")) ?? null;
    return <Autocomplete multiple={multiple} options={options} value={selected}
      disabled={field.disabled} loading={remote.isFetching} filterOptions={(rows) => rows}
      slotProps={{ listbox: { onScroll: (event) => { const element = event.currentTarget; if (element.scrollTop + element.clientHeight >= element.scrollHeight - 30 && remote.hasNextPage && !remote.isFetching) void remote.fetchNextPage(); } } }}
      getOptionLabel={(option) => option.label} isOptionEqualToValue={(a, b) => a.value === b.value}
      onInputChange={(_, text, reason) => { if (reason === "input") setSearch(text); }}
      onChange={(_, option) => { onChange(Array.isArray(option) ? option.map((item) => item.value) : option?.value ?? ""); if (!Array.isArray(option)) onOptionLabel?.(option?.label ?? ""); }}
      noOptionsText={remote.error ? "No se pudieron cargar las opciones" : "Sin resultados"}
      renderInput={(params) => <TextField {...params} label={field.label} required={field.required && !(multiple && Array.isArray(value) && value.length > 0)} error={!!error} helperText={error || field.help_text} />} />;
  }
  const select = field.kind === "select" || field.kind === "multiselect";
  return <TextField fullWidth label={field.label} required={field.required} disabled={field.disabled} placeholder={placeholder}
    error={!!error} helperText={error || field.help_text}
    value={value ?? (field.kind === "multiselect" ? [] : "")}
    select={select} multiline={field.kind === "textarea"} minRows={field.kind === "textarea" ? 3 : undefined}
    type={["date", "time", "number", "email"].includes(field.kind) ? field.kind : "text"}
    slotProps={{ inputLabel: ["date", "time"].includes(field.kind) || placeholder ? { shrink: true } : undefined,
      select: { multiple: field.kind === "multiselect" } }}
    onChange={(event) => onChange(event.target.value)}>
    {select && field.options.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
  </TextField>;
}
