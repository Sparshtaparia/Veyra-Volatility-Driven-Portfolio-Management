import { RefreshCw, ShieldCheck } from "lucide-react"
import { Link } from "react-router-dom"
import { cn } from "cn"
import type { SignalDecision } from "@/api/portfolios"
import { formatDate } from "@/lib/format"

export function DecisionCard({
  result,
  evaluating,
  onEvaluate,
  className,
}: {
  result: SignalDecision
  evaluating?: boolean
  onEvaluate?: () => void
  className?: string
}) {
  const decision = result.allocation_result?.decision ?? "HOLD"
  const isRebalance = decision === "REBALANCE_REQUIRED"
  const regime = result.controls[0]?.regime?.replaceAll("_", " ") ?? "NORMAL"
  const reliability = result.controls[0]?.reliability_state ?? "—"
  const composite = result.composite_risk?.composite_score

  return (
    <section className={cn("overflow-hidden rounded-xl border bg-white", className)}>
      <div className={cn("h-1.5", isRebalance ? "bg-amber-500" : "bg-emerald-500")} />
      <div className="p-6 sm:p-8">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wide">
            <span className="grid size-8 place-items-center rounded-lg bg-slate-950 text-white"><ShieldCheck className="size-4.5" /></span>
            Veyra Decision
          </p>
          <span className={cn("rounded-full px-3 py-1 text-xs font-bold tracking-wide", isRebalance ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900")}>
            {isRebalance ? "ACT ON THIS" : "ON TRACK"}
          </span>
        </div>

        <h2 className={cn("mt-6 text-3xl font-semibold tracking-tight", isRebalance ? "text-amber-900" : "text-emerald-800")}>
          {isRebalance ? "Rebalance required" : "Hold"}
        </h2>
        <p className="mt-2 max-w-md text-slate-600">
          {isRebalance
            ? "Veyra detected meaningful allocation changes. Review the recommended shift and execute a paper rebalance to see the simulated result."
            : "No significant allocation adjustment required. Your portfolio stays aligned with current market, risk and signal conditions."}
        </p>

        <div className="mt-6 grid grid-cols-3 gap-4 rounded-lg bg-slate-50 p-4 text-center">
          <div>
            <p className="text-xs text-slate-500">Market Regime</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{regime}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Portfolio Risk</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{composite != null ? composite.toFixed(2) : "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Reliability</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{reliability}</p>
          </div>
        </div>

        <p className="mt-5 text-xs text-slate-400">Last evaluated {formatDate(result.as_of_date)}</p>

        <div className="mt-5 flex flex-wrap gap-3">
          {isRebalance ? (
            <Link to="/app/evaluation/rebalance" className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-amber-600 px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-700">
              Review Changes
            </Link>
          ) : (
            <button
              onClick={onEvaluate}
              disabled={evaluating}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:pointer-events-none disabled:opacity-60"
            >
              <RefreshCw className={evaluating ? "size-4 animate-spin" : "size-4"} />
              {evaluating ? "Evaluating…" : "Evaluate Portfolio"}
            </button>
          )}
          <Link to="/app/evaluation" className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-300 px-5 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50">
            View details
          </Link>
        </div>
      </div>
    </section>
  )
}