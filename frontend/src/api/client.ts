import { supabase } from "@/lib/supabase"

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
const apiRootUrl = apiBaseUrl.replace(/\/api\/v1\/?$/, "")

export class ApiError extends Error { constructor(public status: number, message: string) { super(message) } }

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const {
      data: { session },
      error,
    } = await supabase.auth.getSession()
    if (error) console.warn("Unable to read Supabase session")
    const headers = new Headers(options.headers)
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json")
    if (session?.access_token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${session.access_token}`)
    }
    response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers })
  } catch { throw new ApiError(0, "Veyra API is not reachable. Start the backend and try again.") }
  if (!response.ok) { const body = await response.json().catch(() => null); throw new ApiError(response.status, body?.detail ?? "The request could not be completed.") }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function apiFetchRoot<T>(path: string): Promise<T> {
  let response: Response
  try { response = await fetch(`${apiRootUrl}${path}`) } catch { throw new ApiError(0, "Veyra API is not reachable. Start the backend and try again.") }
  if (!response.ok) throw new ApiError(response.status, "The system health check could not be completed.")
  return response.json() as Promise<T>
}
