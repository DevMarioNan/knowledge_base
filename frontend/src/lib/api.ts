import { request, ApiError } from "./http";
import { env } from "./env";

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function refreshToken(): Promise<boolean> {
  const token = localStorage.getItem("access_token");
  if (!token) return false;

  try {
    const res = await fetch(`${env.apiBaseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: token }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem("access_token", data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function handleRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  try {
    return await request<T>(`${env.apiBaseUrl}${path}`, {
      method,
      headers: authHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshToken().finally(() => {
          isRefreshing = false;
          refreshPromise = null;
        });
      }

      const refreshed = await refreshPromise;
      if (refreshed) {
        return await request<T>(`${env.apiBaseUrl}${path}`, {
          method,
          headers: authHeaders(),
          body: body ? JSON.stringify(body) : undefined,
        });
      }

      localStorage.removeItem("access_token");
    }
    throw err;
  }
}

export const api = {
  get<T>(path: string) {
    return handleRequest<T>("GET", path);
  },

  post<T>(path: string, body?: unknown) {
    return handleRequest<T>("POST", path, body);
  },

  put<T>(path: string, body?: unknown) {
    return handleRequest<T>("PUT", path, body);
  },

  patch<T>(path: string, body?: unknown) {
    return handleRequest<T>("PATCH", path, body);
  },

  delete<T>(path: string) {
    return handleRequest<T>("DELETE", path);
  },

  upload<T>(path: string, formData: FormData, onProgress?: (pct: number) => void): Promise<T> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const token = localStorage.getItem("access_token");

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText ? JSON.parse(xhr.responseText) : undefined);
        } else {
          let detail = `HTTP ${xhr.status}`;
          try {
            const body = JSON.parse(xhr.responseText);
            detail = body.detail ?? detail;
          } catch {}
          reject(new ApiError(xhr.status, detail, xhr.responseText));
        }
      };

      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.open("POST", `${env.apiBaseUrl}${path}`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.send(formData);
    });
  },
};
