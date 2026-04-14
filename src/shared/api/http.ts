import axios from "axios";

import { env } from "@/shared/config/env";

export const httpClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 10_000,
});

httpClient.interceptors.response.use((response) => response, (error) => Promise.reject(error));
