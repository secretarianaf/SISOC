import axios, { AxiosError } from "axios";

export type { Itinerario, Jornada, Sede, Page, Session, Options, FormField, FormSchema, Registro, Laboratorio } from "./types";

const http = axios.create({
  baseURL: "/api/vpsl",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

function csrfToken(): string {
  try {
    return decodeURIComponent(document.cookie.split("; ").find((part) => part.startsWith("csrftoken="))?.split("=")[1] ?? "");
  } catch {
    return "";
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields?: Record<string, { message: string }[]>) {
    super(message);
  }
}

function throwApiError(error: unknown): never {
  if (!(error instanceof AxiosError)) throw error;
  const status = error.response?.status ?? 0;
  if (status === 401) {
    window.location.assign(`/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
  }
  const data = error.response?.data as Record<string, unknown> | undefined;
  const detail = data?.detail || data?.error || data?.message;
  const fieldErrors: Record<string, { message: string }[]> = {};
  if (status === 400 && data && !detail) {
    for (const [field, messages] of Object.entries(data)) {
      if (Array.isArray(messages)) fieldErrors[field] = messages.map((message) => ({ message: String(message) }));
    }
  }
  throw new ApiError(status, String(detail || "Revisá los datos ingresados."), Object.keys(fieldErrors).length ? fieldErrors : undefined);
}

export async function get<T>(path: string): Promise<T> {
  try {
    const response = await http.get<T>(path);
    return response.data;
  } catch (error) { return throwApiError(error); }
}

export async function postForm<T>(path: string, form: FormData, forceMultipart = false): Promise<T> {
  try {
    const entries = [...form.entries()].filter(([, value]) => !(value instanceof File && value.size === 0 && !value.name));
    const hasFiles = entries.some(([, value]) => value instanceof File);
    const payload = forceMultipart || hasFiles ? form : Object.fromEntries([...new Set(entries.map(([key]) => key))].map((key) => {
      const values = entries.filter(([name]) => name === key).map(([, value]) => value);
      return [key, values.length > 1 || key === "vehiculos" || key === "casos" ? values : values[0]];
    }));
    const response = await http.post<T>(path, payload, { headers: { "X-CSRFToken": csrfToken() } });
    return response.data;
  } catch (error) { return throwApiError(error); }
}

export function initFrontendSentry(module: string): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;
  void import("@sentry/react").then((Sentry) => Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT,
    release: import.meta.env.VITE_RELEASE_SHA,
    sendDefaultPii: false,
    initialScope: { tags: { frontend: `v2-${module}` } },
  })).catch(() => { /* Reporting must not prevent the application from loading. */ });
}
