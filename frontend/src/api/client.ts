import type { Evaluation, FeedbackData, Holding, Portfolio, SignalDecision } from "./portfolios"
import type { PaperExecutionResult } from "@/lib/evaluation-store"
import type { SystemStatus } from "./system"

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const token = localStorage.getItem("auth_token")
    const headers = new Headers(options.headers)
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json")
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(0, "Veyra API is not reachable. Start the backend and try again.")
  }
  
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? "The request could not be completed.")
  }
  
  return response.json() as Promise<T>
}