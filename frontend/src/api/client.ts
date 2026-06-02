import type { Paginated } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
const ACCESS_TOKEN_KEY = "plantcare.access";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string | null) {
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = payload?.detail ?? Object.values(payload ?? {}).flat().join(" ");
    throw new Error(detail || "Ошибка запроса к серверу");
  }

  return payload as T;
}

export function unwrapResults<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

export async function login(username: string, password: string) {
  return apiRequest<{ access: string; refresh: string }>("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function registerUser(username: string, email: string, password: string) {
  return apiRequest("/auth/register/", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}
