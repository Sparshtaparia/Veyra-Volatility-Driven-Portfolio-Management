import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { Link } from "react-router-dom"
import { useEvaluations } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { readLatestEvaluation, readLatestExecution } from "@/lib/evaluation-store"
import { currency, formatDate, percent } from "@/lib/format"
import { Badge, EmptyState, Loading, Notice, Panel } from "@/components/ui/primitives"
import { cn } from "cn"

type ActivityItem = {
  id: string
  date: string
  label: string
  detail: string
  badge: string
  tone: "amber" | "emerald" | "slate"
  evaluation?: NonNullable<ReturnType<typeof readLatestEvaluation>>
}

export function ActivityPage() {
  const portfolioId = getSavedPortfolioId()
  const evaluations = useEvaluations(portfolioId)
  const [expanded, setExpanded] = useState<string | null>(null)

  if (!portfolioId) return <EmptyState title="No activity yet" text="Create a portfolio and run an evaluation to populate your activity." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />

  if (evaluations.isLoading) return <Loading label="Loading activity…" />
  if (evaluations.error) return <Notice text={evaluations.error.message} />

  const latest = portfolioId ? readLatestEvaluation(portfolioId) : null
  const execution = portfolioId ? readLatestExecution(portfolioId) : null

  const items: ActivityItem[] = []
  if (execution) {
    items.push({
      id: `exec-${execution.evaluation_id}`,
      date: new Date().toISOString(),
      label: "Paper Rebalance",
      detail: `${execution.orders.length} orders · ${currency(execution.total_cost)} cost`,
      badge: "COMPLETED",
      tone: "emerald",
    })
  }
  for (const item of evaluations.data ?? []) {
    items.push({
      id: item.evaluation_id,
      date: item.evaluation_date,
      label: "Portfolio Evaluation",
      detail: item.trigger.replaceAll("_", " "),
      badge: item.decision.replaceAll("_", " "),
      tone: item.decision === "REBALANCE_REQUIRED" ? "amber" : "emerald",
      evaluation: latest?.evaluation_id === item.evaluation_id ? latest : undefined,
    })
  }
  items.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  if (items.length === 0) {
    return (
      <Panel className="mx-auto mt-10 max-w-lg">
        <EmptyState title="No activity yet" text="Run an evaluation to see your first Veyra decision here." action={<Link to="/app/evaluation" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Run an evaluation</Link>} />
      </Panel>
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <p className="text-sm font-semibold text-emerald-700">ACTIVITY</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Activity</h1>
        <p className="mt-1 text-sm text-slate-500">A timeline of evaluations and paper executions — click an event to see why Veyra made its decision.</p>
      </header>

      <section className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        {items.map((item, index) => (
          <ActivityRow key={item.id} item={item} index={index} expanded={expanded === item.id} onToggle={() => setExpanded(expanded === item.id ? null : item.id)} />
        ))}
      </section>
    </div>
  )
}

function ActivityRow({ item, index, expanded, onToggle }: { item: ActivityItem; index: number; expanded: boolean; onToggle: () => void }) {
  return (
    <div className={cn("border-slate-100", index > 0 && "border-t")}>
      <button onClick={onToggle} className="flex w-full items-center justify-between gap-4 px-6 py-4 text-left transition-colors hover:bg-slate-50">
        <div className="flex items-center gap-4">
          <span className={cn("h-full w-1 self-stretch rounded-full", item.tone === "amber" ? "bg-amber-400" : item.tone === "emerald" ? "bg-emerald-500" : "bg-slate-300")} />
          <div>
            <p className="text-sm font-semibold text-slate-900">{item.label}</p>
            <p className="mt-0.5 text-xs text-slate-500">{formatDate(item.date)} · {item.detail}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone={item.tone}>{item.badge}</Badge>
          <ChevronDown className={cn("size-4 text-slate-400 transition-transform", expanded && "rotate-180")} />
        </div>
      </button>
      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50 px-6 py-5">
          {item.badge === "COMPLETED" ? (
            <div className="text-sm leading-6 text-slate-600">
              <p>This paper rebalance executed {item.detail}.</p>
              <Link to="/app/evaluation/rebalance" className="mt-3 inline-block text-sm font-semibold text-emerald-700 hover:underline">View execution result →</Link>
            </div>
          ) : item.badge === "HOLD" ? (
            <div className="text-sm leading-6 text-slate-600">
              <p>Veyra evaluated the portfolio on {formatDate(item.date)} and concluded that no allocation change was needed. Market, risk and signal conditions did not warrant a shift.</p>
            </div>
          ) : item.badge.includes("REBALANCE") ? (
            <div className="text-sm leading-6 text-slate-600">
              <p>Veyra detected meaningful allocation changes. Review the recommended shift:</p>
              {item.evaluation?.allocation_result && (
                <ul className="mt-2 space-y-1">
                  {item.evaluation.allocation_result.allocations.map((alloc) => (
                    <li key={alloc.ticker} className="flex justify-between text-slate-700"><span>{alloc.ticker}</span><span>{percent(alloc.current_weight)} → {percent(alloc.target_weight)}</span></li>
                  ))}
                </ul>
              )}
              <Link to="/app/evaluation" className="mt-3 inline-block text-sm font-semibold text-emerald-700 hover:underline">Open decision center →</Link>
            </div>
          ) : (
            <div className="text-sm leading-6 text-slate-600">
              <p>Evaluation completed on {formatDate(item.date)} with decision {item.badge}.</p>
              <Link to="/app/evaluation" className="mt-3 inline-block text-sm font-semibold text-emerald-700 hover:underline">Open decision center →</Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}