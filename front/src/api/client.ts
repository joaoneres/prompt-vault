import axios, { AxiosError } from "axios";

/** Error shape returned by the gateway: { error: { code, message, details } }. */
interface GatewayError {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 15_000,
});

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError<GatewayError>) => {
    const apiError = error.response?.data?.error;
    if (apiError?.message) {
      return Promise.reject(new ApiError(apiError.message, apiError.code ?? "UNKNOWN", error.response?.status));
    }
    if (!error.response) {
      return Promise.reject(new ApiError("Não foi possível conectar à API.", "NETWORK_ERROR"));
    }
    return Promise.reject(
      new ApiError(`Erro inesperado (HTTP ${error.response.status}).`, "UNEXPECTED", error.response.status),
    );
  },
);

export const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
