import { internal, record, text } from "./MainFrame";

/** Shared shapes of the core pages (T02-T06): queued messages, pagination and the Django form projection. */
export type CoreMessage = { message: string; level: "success" | "error" | "warning" | "info" };
export type CoreField = {
  name: string; id: string; label: string; widget: "text" | "checkbox" | "select" | "textarea" | string;
  required: boolean; attrs: Record<string, string>; value: string | boolean; errors: string[];
  choices?: { value: string; label: string }[];
};

const LEVELS = ["success", "error", "warning", "info"];
export const count = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);

export const messagesValid = (v: unknown): v is CoreMessage[] =>
  Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export const fieldValid = (f: unknown): f is CoreField =>
  record(f) && text(f.name) && text(f.id) && text(f.label) && text(f.widget) && typeof f.required === "boolean" &&
  record(f.attrs) && Object.values(f.attrs).every(text) && (text(f.value) || typeof f.value === "boolean") && strings(f.errors) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export const urlsValid = (v: unknown, keys: string[]) => record(v) && keys.every((k) => internal(v[k]));

/** `components/pagination.html` page window: `null` marks a missing neighbour. */
export type CorePagination = { paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[]; count: number };
export const paginationValid = (v: unknown): v is CorePagination =>
  record(v) && typeof v.paginated === "boolean" && count(v.number) && (v.previous === null || count(v.previous)) &&
  (v.next === null || count(v.next)) && Array.isArray(v.range) && v.range.every((n) => count(n) || text(n)) && count(v.count);
