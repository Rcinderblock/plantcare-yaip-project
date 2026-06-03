import type { Paginated } from "../types/api";
import type { User } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export async function apiRequest<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (response.status === 401 && retry && !path.startsWith("/auth/token/") && path !== "/auth/register/") {
    await refreshSession();
    return apiRequest<T>(path, options, false);
  }

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
  return apiRequest<{ user: User; detail: string }>("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function refreshSession() {
  const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Сессия истекла, войдите заново");
  }
}

export async function logout() {
  return apiRequest<{ detail: string }>("/auth/logout/", { method: "POST" }, false);
}

export async function registerUser(username: string, email: string, password: string) {
  return apiRequest("/auth/register/", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}
