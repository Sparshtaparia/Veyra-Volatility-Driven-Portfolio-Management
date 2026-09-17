import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/auth-model"
import { useEvaluatePortfolio, useEvaluations, useHoldings, usePortfolio, getSavedPortfolioId } from "@/hooks/use-portfolio"
import { readLatestEvaluation, writeLatestEvaluation, readLatestExecution } from "@/lib/evaluation-store"
import { currency, formatDate, percent, signedPercent } from "@/lib/format"
import { DecisionCard } from "@/components/decision/decision-card"
import { AllocationLegend } from "@/components/portfolio/portfolio-chart"
import { EmptyState, Loading, Notice, Panel, PanelHeader, Badge } from "@/components/ui/primitives"

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 17) return "Good afternoon"
  return "Good evening"
}

export function AppDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const evaluations = useEvaluations(portfolioId)
  const evaluate = useEvaluatePortfolio(portfolioId)

  const [evaluation, setEvaluation] = useState<ReturnType<typeof readLatestEvaluation>>(() => (portfolioId ? readLatestEvaluation(portfolioId) : null))

  function runEvaluation() {
    if (!portfolioId) return
    evaluate.mutate(undefined, {
      onSuccess: (result) => {
        writeLatestEvaluation(portfolioId, result)
        setEvaluation(result)
        navigate("/app", { replace: true })
      },
    })
  }

  if (!portfolioId) {
    return (
      <Panel className="mx-auto mt-16 max-w-md">
        <EmptyState
          title="No portfolio yet"
          text="Create your first portfolio to let Veyra monitor it and tell you when it needs to change."
          action={<button onClick={() => navigate("/onboarding")} className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</button>}
        />
      </Panel>
    )
  }

  const costBasis = holdings.data?.reduce((sum, h) => sum + h.quantity * h.average_price, 0) ?? null
  const change = costBasis ? (portfolio.data!.total_value - costBasis) / costBasis : null
  const execution = readLatestExecution(portfolioId)
  const recent = evaluations.data?.slice(0, 3) ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-emerald-700">INVESTOR WORKSPACE</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">{greeting()}, {user?.name.split(" ")[0]}</h1>
      </header>

      {(portfolio.error || holdings.error || evaluations.error) && <Notice text={(portfolio.error ?? holdings.error ?? evaluations.error)?.message ?? "Unable to load your portfolio."} />}

      {portfolio.isLoading ? (
        <Loading label="Loading portfolio…" />
      ) : portfolio.data ? (
        <>
          <section className="mt-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-slate-500">{portfolio.data.name}</p>
              <p className="mt-1 text-4xl font-semibold tracking-tight text-slate-950">{currency(portfolio.data.total_value, portfolio.data.currency)}</p>
              {change != null && (
                <p className={`mt-2 text-sm font-semibold ${change >= 0 ? "text-emerald-700" : "text-red-600"}`}>
                  {signedPercent(change)} <span className="font-normal text-slate-500">vs average cost</span>
                </p>
              )}
            </div>
            <button onClick={runEvaluation} disabled={evaluate.isPending} className="inline-flex h-11 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 disabled:opacity-60">
              <RefreshCw className={evaluate.isPending ? "size-4 animate-spin" : "size-4"} /> {evaluate.isPending ? "Evaluating…" : "Evaluate Portfolio"}
            </button>
          </section>

          {evaluate.error && <Notice text={evaluate.error.message} />}

          <section className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_.7fr]">
            {evaluation ? (
              <DecisionCard result={evaluation} evaluating={evaluate.isPending} onEvaluate={runEvaluation} className="h-full" />
            ) : (
              <Panel className="grid h-full place-items-center p-8">
                <div className="max-w-sm text-center">
                  <p className="text-lg font-semibold text-slate-900">No evaluation yet</p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Run your first evaluation to see Veyra's decision, market conditions, and whether your portfolio needs to change.</p>
                  <button onClick={runEvaluation} disabled={evaluate.isPending} className="mt-5 inline-flex h-11 items-center gap-2 rounded-lg bg-emerald-600 px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:opacity-60">
                    <RefreshCw className={evaluate.isPending ? "size-4 animate-spin" : "size-4"} /> Evaluate Portfolio
                  </button>
                </div>
              </Panel>
            )}

            <div className="space-y-6">
              <Panel className="p-6">
                <h2 className="text-base font-semibold text-slate-950">Portfolio overview</h2>
                {holdings.data?.length ? <div className="mt-4"><AllocationLegend holdings={holdings.data} /></div> : <EmptyState title="No holdings" text="Add holdings to see your allocation." />}
              </Panel>

              {evaluation && <RiskSnapshot result={evaluation} />}
            </div>
          </section>

          <section className="mt-6">
            <Panel>
              <PanelHeader title="Recent activity" action={<button onClick={() => navigate("/app/activity")} className="text-sm font-semibold text-emerald-700 hover:underline">View all</button>} />
              <div className="divide-y divide-slate-100 px-6">
                {execution && (
                  <ActivityRow date={new Date().toISOString()} label="Paper Rebalance" detail="2 BUY/SELL orders FILLED" badge="COMPLETED" tone="emerald" onOpen={() => navigate("/app/evaluation/rebalance")} />
                )}
                {recent.length === 0 && !execution ? (
                  <p className="py-8 text-center text-sm text-slate-500">No activity yet — run an evaluation to see your first decision.</p>
                ) : (
                  recent.map((item) => (
                    <ActivityRow
                      key={item.evaluation_id}
                      date={item.evaluation_date}
                      label="Portfolio Evaluation"
                      detail={item.trigger.replaceAll("_", " ")}
                      badge={item.decision.replaceAll("_", " ")}
                      tone={item.decision !== "HOLD" ? "amber" : "emerald"}
                      onOpen={() => navigate("/app/activity")}
                    />
                  ))
                )}
              </div>
            </Panel>
          </section>
        </>
      ) : null}
    </div>
  )
}

function RiskSnapshot({ result }: { result: NonNullable<ReturnType<typeof readLatestEvaluation>> }) {
  const risk = result.composite_risk
  const control = result.controls[0]
  return (
    <Panel className="p-6">
      <h2 className="text-base font-semibold text-slate-950">Risk snapshot</h2>
      {!risk && !control ? (
        <p className="mt-3 text-sm text-slate-500">No risk signals recorded.</p>
      ) : (
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex items-center justify-between"><dt className="text-slate-500">Volatility</dt><dd className="font-semibold">{control ? percent(control.volatility_state) : "—"}</dd></div>
          <div className="flex items-center justify-between"><dt className="text-slate-500">Reliability</dt><dd className="font-semibold">{control?.reliability_state ?? "—"}</dd></div>
          <div className="flex items-center justify-between"><dt className="text-slate-500">Composite Risk</dt><dd className="font-semibold">{risk ? risk.composite_score.toFixed(2) : "—"}</dd></div>
          <div className="flex items-center justify-between"><dt className="text-slate-500">Regime</dt><dd className="font-semibold">{control?.regime.replaceAll("_", " ") ?? "—"}</dd></div>
        </dl>
      )}
    </Panel>
  )
}

function ActivityRow({ date, label, detail, badge, tone, onOpen }: { date: string; label: string; detail: string; badge: string; tone: "amber" | "emerald"; onOpen: () => void }) {
  return (
    <button onClick={onOpen} className="flex w-full items-center justify-between gap-4 py-3.5 text-left">
      <div className="flex items-center gap-3">
        <span className={`size-2 shrink-0 rounded-full ${tone === "amber" ? "bg-amber-500" : "bg-emerald-500"}`} />
        <div>
          <p className="text-sm font-medium text-slate-900">{label}</p>
          <p className="text-xs text-slate-500">{formatDate(date)} · {detail}</p>
        </div>
      </div>
      <Badge tone={tone}>{badge}</Badge>
    </button>
  )
}
