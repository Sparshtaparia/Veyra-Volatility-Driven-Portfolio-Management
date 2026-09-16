import { apiFetch } from "@/api/client"

export type SystemStatus = {
  environment: string
  database: { status: string; schema_status: string; reachable: boolean }
  scheduler: { running: boolean; job_count?: number; jobs?: Record<string, unknown> }
  market_data: { provider: string; cache: Record<string, unknown> }
  scheduled_run_counts: Record<string, number>
  recent_runs: Array<{ run_id: string; job_name: string; status: string; started_at: string; completed_at?: string | null }>
  metrics: Record<string, number>
}

export const systemApi = {
  status: () => apiFetch<SystemStatus>("/system/status"),
}