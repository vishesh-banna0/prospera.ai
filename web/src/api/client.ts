/**
 * One HTTP client, one error surface. Every request goes through here.
 *
 * The backend returns errors as `{ "detail": "..." }` on 400/404/500. We surface
 * `detail` verbatim because the backend's messages are specific and useful — we
 * never replace them with a generic "Something went wrong."
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * True only when the backend market-data key is genuinely missing / not
 * configured. Deliberately narrow: a provider 403 (see isPlanLimitError) means
 * the key works but the plan doesn't cover that symbol — a different situation.
 */
export function isMissingKeyError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  return /not configured|no api key|api key (is )?(missing|required|not set)|key is required/i.test(
    error.message,
  );
}

/**
 * True when the upstream provider refused the request (HTTP 403). On Finnhub's
 * free plan this is what NSE/BSE and other non-US exchanges return for live
 * quotes — the key is valid, the exchange just isn't included.
 */
export function isPlanLimitError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  return /\b403\b|forbidden/i.test(error.message);
}

type Json = Record<string, unknown> | unknown[];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    // Network failure — the dev backend is probably not running.
    throw new ApiError(
      `Can't reach the backend at ${API_BASE_URL}. Is it running?`,
      0,
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const body = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    throw new ApiError(extractDetail(body) ?? `Request failed (${res.status})`, res.status);
  }
  return body as T;
}

/** FastAPI's `detail` is usually a string, sometimes a validation array. */
function extractDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) =>
          d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d),
        )
        .join("; ");
    }
  }
  return null;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: Json) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: Json) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
