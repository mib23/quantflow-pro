const dataSource = (import.meta.env.VITE_DATA_SOURCE ?? "api") as "mock" | "api";

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  wsBaseUrl: import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/ws",
  dataSource,
};
