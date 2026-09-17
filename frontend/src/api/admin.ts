import { apiFetch } from "@/api/client"

export type ApiHealth = {
  status: string
}

export type DatabaseReadiness = {
  status: string
  schema_status?: string
  current_migration?: string | null
  database?: string
}

export type RecentRun = {
  run_id: string
  run_type: string
  portfolio_id: string
  evaluation_date: string
  evaluation_id: string | null
  status: string
  provider: string
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  error_type: string | null
}

export type SystemStatusResponse = {
  environment: string
  database: Record<string, string>
  scheduler: {
    running?: boolean
    jobs?: Array<{ id: string; name: string; next_run_time: string | null }>
    [key: string]: unknown
  }
  market_data: {
    provider?: string
    cache?: Record<string, unknown>
    [key: string]: unknown
  }
  scheduled_run_counts: Record<string, number>
  recent_runs: RecentRun[]
  metrics: Record<string, unknown>
}

export const adminApi = {
  health: () => apiFetch<ApiHealth>("/health"),
  readiness: () => apiFetch<DatabaseReadiness>("/health/ready"),
  systemStatus: () => apiFetch<SystemStatusResponse>("/system/status"),
}
