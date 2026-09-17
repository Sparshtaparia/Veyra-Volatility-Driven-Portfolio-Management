import { AlertTriangle, CheckCircle2, LoaderCircle, RefreshCw } from "lucide-react"
import { useAdminHealth } from "@/hooks/use-admin-health"

interface SystemHealthCardProps {
  compact?: boolean
}

export function SystemHealthCard({ compact = false }: SystemHealthCardProps) {
  const { data, isLoading, isFetching, error, refetch, dataUpdatedAt } = useAdminHealth()

  const isOperational = data?.status === "live" || data?.status === "ok"
  const hasError = Boolean(error) || (!isLoading && !isOperational)

  const lastCheckedText = dataUpdatedAt
    ? new Intl.DateTimeFormat("en-IN", {
        hour: "numeric",
        minute: "numeric",
        second: "numeric",
        hour12: true,
      }).format(new Date(dataUpdatedAt))
    : null

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span
            className={`grid size-10 place-items-center rounded-lg transition-colors ${
              isLoading
                ? "bg-slate-100 text-slate-500"
                : isOperational
                ? "bg-emerald-100 text-emerald-700"
                : "bg-rose-100 text-rose-700"
            }`}
          >
            {isLoading ? (
              <LoaderCircle className="size-5 animate-spin" />
            ) : isOperational ? (
              <CheckCircle2 className="size-5" />
            ) : (
              <AlertTriangle className="size-5" />
            )}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">API Health</h2>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                  isLoading
                    ? "bg-slate-100 text-slate-600"
                    : isOperational
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-rose-50 text-rose-700 border border-rose-200"
                }`}
              >
                {isLoading ? "Checking…" : isOperational ? "Operational" : "Unavailable"}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">Live query: GET /health</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50 transition"
          aria-label="Refresh API health status"
        >
          <RefreshCw className={`size-3.5 ${isFetching ? "animate-spin text-slate-950" : ""}`} />
          <span>{isFetching ? "Checking…" : "Check again"}</span>
        </button>
      </div>

      {!compact && (
        <div className="mt-4 pt-4 border-t border-slate-100 text-xs text-slate-600 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Service status:</span>
            <span className="font-medium font-mono text-slate-800">
              {isLoading ? "Connecting…" : isOperational ? "status: ok" : "unreachable"}
            </span>
          </div>

          {lastCheckedText && (
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Last verified:</span>
              <span className="text-slate-700">{lastCheckedText}</span>
            </div>
          )}

          {hasError && (
            <p className="mt-2 rounded bg-rose-50 p-2.5 text-xs text-rose-700 border border-rose-100">
              {error instanceof Error
                ? error.message
                : "Veyra API did not return an OK response. Verify the backend service is running."}
            </p>
          )}
        </div>
      )}
    </article>
  )
}
