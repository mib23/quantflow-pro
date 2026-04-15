import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

import { env } from "@/shared/config/env";
import { refreshSession } from "@/shared/api/auth";
import { useSessionStore } from "@/entities/user/store";

export const httpClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 10_000,
});

httpClient.interceptors.request.use((config) => {
  const accessToken = useSessionStore.getState().accessToken;

  if (accessToken) {
    config.headers = config.headers ?? {};
    if (!("Authorization" in config.headers) && !(config.headers as Record<string, string>).Authorization) {
      (config.headers as Record<string, string>).Authorization = `Bearer ${accessToken}`;
    }
  }

  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    if (!error.response || error.response.status !== 401 || !originalRequest || originalRequest._retry || isAuthRequest(originalRequest.url)) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const session = await refreshSession();
      originalRequest.headers = originalRequest.headers ?? {};
      (originalRequest.headers as Record<string, string>).Authorization = `Bearer ${session.accessToken}`;
      return httpClient.request(originalRequest);
    } catch (refreshError) {
      useSessionStore.getState().clearSession();
      return Promise.reject(error);
    }
  },
);

function isAuthRequest(url?: string) {
  return Boolean(url && (url.includes("/auth/login") || url.includes("/auth/refresh") || url.includes("/auth/logout")));
}
