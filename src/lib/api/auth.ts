import { apiClient } from "./client";

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  preferred_size?: string | null;
  style_keywords?: string | null;
  is_active?: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SignupPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface UpdateProfilePayload {
  full_name?: string;
  preferred_size?: string;
  style_keywords?: string;
}

const TOKEN_KEY = "catalogiq.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function loginUser(payload: LoginPayload): Promise<{ access_token: string }> {
  const response = await apiClient.post<{ access_token: string }>("/auth/login", payload);
  if (response.data.access_token) {
    setToken(response.data.access_token);
  }
  return response.data;
}

export async function signupUser(payload: SignupPayload): Promise<{ access_token: string }> {
  const response = await apiClient.post<{ access_token: string }>("/auth/signup", payload);
  if (response.data.access_token) {
    setToken(response.data.access_token);
  }
  return response.data;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>("/auth/me");
  return response.data;
}

export async function updateCurrentUserProfile(
  payload: UpdateProfilePayload,
): Promise<UserProfile> {
  const response = await apiClient.put<UserProfile>("/auth/profile", payload);
  return response.data;
}
