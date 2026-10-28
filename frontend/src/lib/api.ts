/** Browser API client.

The login token stays in an HttpOnly cookie. The CSRF value is kept in memory
for this tab and sent as X-CSRF-Token. It is not written to localStorage.
*/
export class ApiError extends Error {
  status: number;
  code: string;
  fields: { field: string; message: string }[];

  constructor(status: number, code: string, message: string, fields: { field: string; message: string }[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

let csrfToken: string | null = null;
let authFailure: ((code: string) => void) | null = null;

export function onAuthFailure(handler: (code: string) => void) {
  authFailure = handler;
}

export function clearCsrf() {
  csrfToken = null;
}

export function newRequestKey() {
  return crypto.randomUUID();
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: { code?: string; message?: string; errors?: { field: string; message: string }[] } };
    const detail = body.detail ?? {};
    return new ApiError(response.status, detail.code ?? "error", detail.message ?? "The request failed.", detail.errors ?? []);
  } catch {
    return new ApiError(response.status, "error", "The request failed.");
  }
}

export async function ensureCsrf(force = false): Promise<string> {
  if (csrfToken && !force) return csrfToken;
  let response: Response;
  try {
    response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  } catch {
    throw new ApiError(0, "api_unavailable", "The Elqovanta EV service is not responding. Start the backend and refresh this page.");
  }
  if (!response.ok) throw await readError(response);
  const body = (await response.json()) as { csrf_token: string };
  csrfToken = body.csrf_token;
  return csrfToken;
}

export async function api<T>(path: string, options: { method?: string; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const send = async (refreshCsrf: boolean) => {
    const headers = new Headers();
    if (options.body !== undefined) headers.set("Content-Type", "application/json");
    if (method !== "GET" && method !== "HEAD") {
      headers.set("X-CSRF-Token", await ensureCsrf(refreshCsrf));
    }
    try {
      return await fetch(`/api/v1${path}`, {
        method,
        credentials: "include",
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
      });
    } catch {
      throw new ApiError(0, "api_unavailable", "The Elqovanta EV service is not responding. Start the backend and refresh this page.");
    }
  };

  let response = await send(false);
  if (response.status === 403) {
    const error = await readError(response.clone());
    if (error.code === "csrf_failed") response = await send(true);
    else throw error;
  }
  if (response.status === 401) {
    const error = await readError(response);
    if (path !== "/auth/me" && path !== "/auth/login" && path !== "/auth/register") authFailure?.(error.code);
    throw error;
  }
  if (!response.ok) throw await readError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
