import axios, { AxiosError } from "axios";

export const TOKEN_KEY = "brightloop_access_token";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 20_000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.includes("/auth/login")
    ) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("brightloop:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export function apiMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return detail.map((item) => item.msg).join(" · ");
    if (error.code === "ECONNABORTED")
      return "The request took too long. Please try again.";
  }
  return "Something went wrong. Please try again.";
}
