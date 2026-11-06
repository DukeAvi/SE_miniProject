export type ApiErrorBody = {
  error?: { message?: string; code?: string; details?: Record<string, string[]> };
};

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, string[]>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error?.message ?? "The request could not be completed.");
    this.name = "ApiError";
    this.status = status;
    this.code = body.error?.code;
    this.details = body.error?.details;
  }
}

let csrfToken: string | null = null;

export async function refreshCsrfToken() {
  const response = await fetch("/api/v1/auth/csrf", {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  const body = (await response.json()) as { csrfToken?: string };
  if (!response.ok || !body.csrfToken) {
    throw new Error("Could not start a secure session. Refresh the page and try again.");
  }
  csrfToken = body.csrfToken;
  return csrfToken;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", csrfToken ?? (await refreshCsrfToken()));
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers,
  });

  if (response.status === 204) return undefined as T;
  const body = (await response.json().catch(() => ({}))) as ApiErrorBody & T;
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

export function friendlyError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has ended. Sign in again to continue.";
    if (error.status === 403) return "This action is not available for your account role.";
    const firstFieldError = Object.values(error.details ?? {})[0]?.[0];
    return firstFieldError ?? error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export type Page<T> = { count: number; page: number; page_size: number; results: T[] };
export type Profile = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: "DONOR" | "RECIPIENT" | "STAFF" | "ADMIN";
};

export const bloodGroups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];
export const components = ["WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS"];

export function localDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export function readable(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value.replaceAll("_", " ");
  return String(value);
}
