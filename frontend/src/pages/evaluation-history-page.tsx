import { useQuery } from "@tanstack/react-query"
import {
  BarChart2,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock,
  History,
  LoaderCircle,
  Play,
  ShieldCheck,
  XCircle,
} from "lucide-react"
import { Link } from "react-router-dom"
import { InvestorShell } from "@/components/layout/investor-shell"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { portfolioApi } from "@/api/portfolios"
import type { Evaluation } from "@/api/portfolios"
import { SkeletonTable } from "@/components/common/skeleton"

// ─── Helpers ──────────────────────────────────────────────────────────────

const formatDate = (v: string) =>
  new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(v))

const humanize = (v: string) =>
  v.replaceAll("_", " ").toLowerCase().replace(/^./, (l) => l.toUpperCase())

// ─── Badge helpers ─────────────────────────────────────────────────────────

function DecisionBadge({ decision }: { decision: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    HOLD:               { label: "Hold",     cls: "bg-emerald-50 text-emerald-800 border border-emerald-200" },
    REVIEW_ALLOCATION:  { label: "Review",   cls: "bg-amber-50 text-amber-800 border border-amber-200" },
    REBALANCE:          { label: "Rebalance",cls: "bg-rose-50 text-rose-800 border border-rose-200" },
  }
  const { label, cls } = map[decision] ?? { label: humanize(decision), cls: "bg-slate-100 text-slate-700" }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {label}
    </span>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status.toUpperCase()) {
    case "COMPLETED": return <CheckCircle2 className="size-4 text-emerald-600" />
    case "FAILED":    return <XCircle      className="size-4 text-rose-600" />
    case "PENDING":   return <Clock        className="size-4 text-amber-500" />
    default:          return <LoaderCircle className="size-4 animate-spin text-slate-400" />
  }
}

// ─── Summary stats ────────────────────────────────────────────────────────

function SummaryBar({ evals }: { evals: Evaluation[] }) {
  const total   = evals.length
  const holds   = evals.filter((e) => e.decision === "HOLD").length
  const rebalances = evals.filter((e) => e.decision !== "HOLD").length
  const lastDate = evals[0]?.evaluation_date ? formatDate(evals[0].evaluation_date) : "—"

  const stats = [
    { label: "Total Evaluations", value: String(total),    icon: <ClipboardList className="size-4 text-emerald-600" /> },
    { label: "Hold Decisions",    value: String(holds),    icon: <ShieldCheck   className="size-4 text-emerald-600" /> },
    { label: "Rebalance Signals", value: String(rebalances),icon:<BarChart2     className="size-4 text-amber-600" /> },
    { label: "Last Evaluated",    value: lastDate,         icon: <Clock         className="size-4 text-slate-500" /> },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((s) => (
        <div key={s.label} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-slate-50">{s.icon}</span>
          <div>
            <p className="text-xs text-slate-500">{s.label}</p>
            <p className="text-base font-bold tabular-nums text-slate-900 leading-tight">{s.value}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Evaluation row ────────────────────────────────────────────────────────

function EvalRow({ ev, index }: { ev: Evaluation; index: number }) {
  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer group animate-fade-up" style={{ animationDelay: `${index * 40}ms` }}>
      <td className="px-5 py-4">
        <div className="flex items-center gap-2">
          <StatusIcon status={ev.status} />
          <span className="text-xs text-slate-400">{ev.evaluation_id.slice(0, 8)}…</span>
        </div>
      </td>
      <td className="px-4 py-4 text-sm text-slate-700 tabular-nums">
        {formatDate(ev.evaluation_date)}
      </td>
      <td className="px-4 py-4">
        <DecisionBadge decision={ev.decision} />
      </td>
      <td className="px-4 py-4 text-sm text-slate-600 capitalize">
        {humanize(ev.trigger)}
      </td>
      <td className="px-5 py-4">
        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
          ev.status.toUpperCase() === "COMPLETED"
            ? "bg-emerald-50 text-emerald-800"
            : ev.status.toUpperCase() === "FAILED"
            ? "bg-rose-50 text-rose-800"
            : "bg-amber-50 text-amber-800"
        }`}>
          {humanize(ev.status)}
        </span>
      </td>
      <td className="px-5 py-4 text-right">
        <ChevronRight className="ml-auto size-4 text-slate-300 group-hover:text-slate-600 transition" />
      </td>
    </tr>
  )
}

// ─── Empty state ───────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center py-20 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-emerald-50 text-emerald-600">
        <History className="size-7" />
      </span>
      <p className="mt-4 text-base font-semibold text-slate-900">No evaluations yet</p>
      <p className="mt-1 text-sm text-slate-500 max-w-xs">
        Run your first evaluation to see how Veyra analyses your portfolio.
      </p>
      <Link
        to="/app/evaluation"
        className="mt-5 inline-flex h-10 items-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 transition"
      >
        <Play className="size-3.5 fill-white" /> Run Evaluation
      </Link>
    </div>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────

export function EvaluationHistoryPage() {
  const portfolioId = getSavedPortfolioId()
  const evals = useQuery({
    queryKey: ["evaluations", portfolioId],
    queryFn: () => portfolioApi.listEvaluations(portfolioId!),
    enabled: !!portfolioId,
  })

  const loading = evals.isPending
  const data = evals.data ?? []

  return (
    <InvestorShell>
      <div className="px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">History</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-900">Evaluation History</h1>
            <p className="mt-1 text-sm text-slate-500">
              A full log of every time Veyra has analysed your portfolio.
            </p>
          </div>
          <Link
            to="/app/evaluation"
            className="shrink-0 inline-flex h-11 items-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 transition"
          >
            <Play className="size-4 fill-white" /> New Evaluation
          </Link>
        </div>

        {!portfolioId ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
            No portfolio found. <Link to="/app/portfolio" className="font-semibold text-emerald-700 hover:underline">Create one</Link>.
          </div>
        ) : loading ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="h-16 rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm skeleton" />
              ))}
            </div>
            <SkeletonTable rows={6} />
          </>
        ) : data.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <EmptyState />
          </div>
        ) : (
          <>
            <SummaryBar evals={data} />

            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div className="flex items-center gap-2">
                  <ClipboardList className="size-4 text-emerald-600" />
                  <p className="text-sm font-semibold text-slate-900">All Evaluations</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
                  {data.length}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                    <tr>
                      <th className="px-5 py-3 text-left">ID</th>
                      <th className="px-4 py-3 text-left">Date &amp; Time</th>
                      <th className="px-4 py-3 text-left">Decision</th>
                      <th className="px-4 py-3 text-left">Trigger</th>
                      <th className="px-5 py-3 text-left">Status</th>
                      <th className="px-5 py-3" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((ev, i) => (
                      <EvalRow key={ev.evaluation_id} ev={ev} index={i} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </InvestorShell>
  )
}
