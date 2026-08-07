import axios from "axios";

/**
 * Central Axios instance for the CatalogIQ AI backend.
 * Base URL can be overridden with VITE_API_BASE_URL.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env['VITE_API_BASE_URL'] ?? "/api",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("catalogiq.token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
);

/**
 * The backend is assumed to exist. While it is unreachable (local/preview),
 * requests fall back to catalog fixtures so the UI stays fully explorable.
 */
export async function requestWithFallback<T>(
  request: () => Promise<{ data: T }>,
  fallback: () => T | Promise<T>,
): Promise<T> {
  try {
    const { data } = await request();
    return data;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 450));
    return fallback();
  }
}
