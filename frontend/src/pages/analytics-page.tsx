import { Link } from "react-router-dom"
import { useEvaluations, useFeedback, useHoldings, usePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { readLatestEvaluation, readLatestExecution } from "@/lib/evaluation-store"
import { currency, formatDate, percent, signedPercent } from "@/lib/format"
import { Badge, EmptyState, Loading, Metric, Notice, Panel, PanelHeader } from "@/components/ui/primitives"
import { cn } from "cn"

export function AnalyticsPage() {
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const evaluations = useEvaluations(portfolioId)
  const feedback = useFeedback(portfolioId)

  if (!portfolioId) return <EmptyState title="No analytics yet" text="Create a portfolio to see performance and risk analytics." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />

  if (portfolio.isLoading || holdings.isLoading) return <Loading label="Loading analytics…" />
  if (portfolio.error) return <Notice text={portfolio.error.message} />

  const evaluation = portfolioId ? readLatestEvaluation(portfolioId) : null
  const execution = portfolioId ? readLatestExecution(portfolioId) : null

  const costBasis = holdings.data?.reduce((sum, h) => sum + h.quantity * h.average_price, 0) ?? null
  const totalValue = portfolio.data?.total_value ?? 0
  const cumulative = costBasis ? (totalValue - costBasis) / costBasis : null
  const volatility = evaluation?.controls[0]?.volatility_state ?? null
  const turnover = evaluation?.allocation_result?.total_turnover ?? null
  const rebalances = (evaluations.data ?? []).filter((item) => item.decision !== "HOLD").length + (execution ? 1 : 0)

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-emerald-700">ANALYTICS</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Performance & Risk</h1>
        <p className="mt-1 text-sm text-slate-500">A plain-language view of how your portfolio has behaved. Benchmark comparisons become richer as history accumulates.</p>
      </header>

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Portfolio Value" value={currency(totalValue)} />
        <Metric label="Cumulative Return" value={cumulative != null ? signedPercent(cumulative) : "—"} hint={cumulative != null ? "vs average cost" : undefined} />
        <Metric label="Annualized Return" value="—" hint="Unavailable until >1 year of history" />
        <Metric label="Volatility" value={volatility != null ? percent(volatility) : "—"} hint="Latest evaluation" />
        <Metric label="Turnover" value={turnover != null ? percent(Math.min(turnover, 1)) : "—"} hint="Latest target change" />
        <Metric label="Rebalances" value={String(rebalances)} hint="Paper executions recommended" />
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
        <Panel>
          <PanelHeader title="Risk metrics" subtitle="From the latest evaluation" />
          <div className="p-6">
            {evaluation ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {evaluation.composite_risk && (
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Composite Risk</p>
                    <p className="mt-2 text-2xl font-semibold">{evaluation.composite_risk.composite_score.toFixed(2)}</p>
                    <Badge tone={evaluation.composite_risk.risk_state === "LOW_RISK" ? "emerald" : evaluation.composite_risk.risk_state === "CRITICAL_RISK" ? "red" : "amber"} className="mt-2">{evaluation.composite_risk.risk_state.replaceAll("_", " ")}</Badge>
                    <dl className="mt-4 space-y-2 text-sm">
                      <Row label="Volatility exposure" value={(evaluation.composite_risk.components.volatility_exposure).toFixed(2)} />
                      <Row label="Concentration" value={(evaluation.composite_risk.components.concentration).toFixed(2)} />
                    </dl>
                  </div>
                )}
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Drawdown</p>
                    <p className="mt-2 text-xl font-semibold">—</p>
                    <p className="mt-1 text-xs text-slate-400">Tracked after more history</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Correlation</p>
                    <p className="mt-2 text-xl font-semibold">—</p>
                    <p className="mt-1 text-xs text-slate-400">Tracked after more history</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Run an evaluation to populate risk analytics.</p>
            )}
          </div>
        </Panel>

        <AdaptiveThresholdCard feedback={feedback.data} />
      </section>

      <section className="mt-6">
        <Panel>
          <PanelHeader title="Benchmark preview" subtitle="Once enough history accrues, Veyra will compare its decisions against simple alternatives." />
          <div className="grid gap-4 p-6 sm:grid-cols-3">
            <BenchmarkCard name="Veyra" note="Volatility-driven decisions" tone="emerald" />
            <BenchmarkCard name="Equal Weight" note="Static 1/N allocation" tone="slate" />
            <BenchmarkCard name="Buy & Hold" note="Your original holdings" tone="slate" />
          </div>
        </Panel>
      </section>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between"><dt className="text-slate-500">{label}</dt><dd className="font-semibold tabular-nums text-slate-900">{value}</dd></div>
}

function BenchmarkCard({ name, note, tone }: { name: string; note: string; tone: "emerald" | "slate" }) {
  return (
    <div className={cn("rounded-lg border p-5", tone === "emerald" ? "border-emerald-200 bg-emerald-50" : "border-slate-200")}>
      <p className="font-semibold">{name}</p>
      <p className="mt-1 text-sm text-slate-500">{note}</p>
      <p className="mt-4 text-2xl font-semibold text-slate-400">—</p>
      <p className="text-xs text-slate-400">Return</p>
    </div>
  )
}

function AdaptiveThresholdCard({ feedback }: { feedback: FeedbackData | null | undefined }) {
  const pct = (v: number) => `${(v * 100).toFixed(3)}%`
  if (!feedback) {
    return (
      <Panel>
        <PanelHeader title="Adaptive Threshold" subtitle="Feedback loop status" />
        <p className="px-6 py-6 text-sm leading-6 text-slate-500">The adaptive threshold updates after each paper rebalance. Complete one to see the previous, observed and updated values here.</p>
      </Panel>
    )
  }
  return (
    <Panel className="border-indigo-200">
      <PanelHeader title="Adaptive Threshold" subtitle="Updated after the last paper rebalance" />
      <div className="p-6">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Previous</p>
            <p className="mt-1.5 text-lg font-semibold">{pct(feedback.previous_threshold)}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Observed</p>
            <p className="mt-1.5 text-lg font-semibold">{pct(feedback.observed_volatility)}</p>
          </div>
          <div className="rounded-lg bg-indigo-700 p-3">
            <p className="text-xs text-indigo-200">Updated</p>
            <p className="mt-1.5 text-lg font-semibold text-white">{pct(feedback.updated_threshold)}</p>
          </div>
        </div>
        <p className="mt-4 text-xs leading-5 text-slate-500">The error between observed volatility and the threshold was {feedback.feedback_error > 0 ? "+" : ""}{pct(feedback.feedback_error)}. The updated threshold will be used in the next evaluation.</p>
        <p className="mt-2 text-xs text-slate-400">As of {formatDate(feedback.timestamp)}</p>
        <div className="mt-5 rounded-lg bg-slate-50 p-3">
          <svg viewBox="0 0 200 48" className="h-12 w-full" aria-hidden="true">
            <polyline points="0,34 50,30 100,33 150,20 200,12" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
            <circle cx="200" cy="12" r="3.5" fill="#4f46e5" />
          </svg>
        </div>
        <p className="mt-2 text-xs text-slate-400">Threshold history (schematic) — grows after each rebalance cycle.</p>
      </div>
    </Panel>
  )
}

type FeedbackData = { previous_threshold: number; observed_volatility: number; feedback_error: number; updated_threshold: number; timestamp: string }
