export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNetworkError(): boolean {
    return false;
  }
}

export class NetworkError extends Error {
  constructor(cause: unknown) {
    super("Unable to connect to the server. Please check your connection and try again.", { cause });
    this.name = "NetworkError";
  }

  get isNetworkError(): boolean {
    return true;
  }
}

export const STATUS_MESSAGES: Record<number, string> = {
  400: "The request was invalid. Please check your input and try again.",
  401: "Your session has expired. Please log in again.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "This operation conflicts with the current state. Please refresh and try again.",
  422: "Please check your input and try again.",
  429: "Too many requests. Please wait a moment and try again.",
};

export function getErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) {
    return err.message;
  }
  if (err instanceof ApiError) {
    if (err.status >= 500) {
      return "The server encountered an error. Please try again later.";
    }
    return STATUS_MESSAGES[err.status] || err.message || "An unexpected error occurred.";
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "An unexpected error occurred. Please try again.";
}

export async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (err) {
    throw new NetworkError(err);
  }

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text().catch(() => null);
    }
    throw new ApiError(
      res.status,
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : STATUS_MESSAGES[res.status] || res.statusText,
      body
    );
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
