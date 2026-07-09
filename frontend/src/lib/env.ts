const required = (key: string, fallback?: string): string => {
  const val = import.meta.env[key] ?? fallback;
  if (val === undefined || val === "") {
    throw new Error(`Missing required env var: ${key}`);
  }
  return val;
};

export const env = {
  apiBaseUrl: required("VITE_API_BASE_URL", "http://localhost:8000"),
};
