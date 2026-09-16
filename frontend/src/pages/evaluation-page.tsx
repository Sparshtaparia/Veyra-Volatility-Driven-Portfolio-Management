import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { Link } from "react-router-dom"
import { useEvaluatePortfolio, useHoldings, usePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { readLatestEvaluation, writeLatestEvaluation } from "@/lib/evaluation-store"
import { currency, formatDate, percent, signedPercent } from "@/lib/format"
import { previewOrders, previewTurnover } from "@/lib/rebalance-preview"
import { EmptyState, Loading, Notice, Panel, PanelHeader, PrimaryButton } from "@/components/ui/primitives"
import { cn } from "cn"

export function EvaluationPage() {
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const evaluate = useEvaluatePortfolio(portfolioId)

  const [result, setResult] = useState<ReturnType<typeof readLatestEvaluation>>(() => (portfolioId ? readLatestEvaluation(portfolioId) : null))

  function run() {
    if (!portfolioId) return
    evaluate.mutate(undefined, { onSuccess: (value) => { writeLatestEvaluation(portfolioId, value); setResult(value) } })
  }

  if (!portfolioId) return <EmptyState title="No portfolio yet" text="Create a portfolio before evaluating." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />

  return (
    <div className="mx-auto max-w-5xl">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-emerald-700">EVALUATION</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Portfolio Evaluation</h1>
          <p className="mt-1 text-sm text-slate-500">Veyra's assessment of your portfolio, translated into investor language.</p>
        </div>
        <PrimaryButton onClick={run} disabled={evaluate.isPending || !portfolio.data}>
          <RefreshCw className={evaluate.isPending ? "size-4 animate-spin" : "size-4"} /> {evaluate.isPending ? "Evaluating…" : "Evaluate Portfolio"}
        </PrimaryButton>
      </header>

      {evaluate.error && <Notice text={evaluate.error.message} />}

      {portfolio.isLoading || holdings.isLoading ? (
        <Loading label="Loading evaluation…" />
      ) : !result ? (
        <Panel className="mt-6">
          <EmptyState
            title="No evaluation yet"
            text="Run an evaluation to see the market state, Veyra's signal, reliability, risk and the recommended decision."
            action={<button onClick={run} disabled={evaluate.isPending} className="inline-flex h-11 items-center gap-2 rounded-lg bg-emerald-600 px-5 text-sm font-semibold text-white disabled:opacity-60"><RefreshCw className="size-4" /> Evaluate Portfolio</button>}
          />
        </Panel>
      ) : (
        <div className="mt-6 space-y-6">
          <section className="grid gap-6 md:grid-cols-2">
            <MarketState result={result} />
            <SignalAndReliability result={result} />
          </section>

          <DecisionNarrative result={result} portfolioValue={portfolio.data?.total_value ?? 0} holdings={holdings.data ?? []} />
        </div>
      )}
    </div>
  )
}

function MarketState({ result }: { result: NonNullable<ReturnType<typeof readLatestEvaluation>> }) {
  const control = result.controls[0]
  const risk = result.composite_risk
  return (
    <Panel>
      <PanelHeader title="Market State" />
      <div className="grid grid-cols-2 gap-4 p-6">
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Regime</p>
          <p className="mt-2 text-lg font-semibold">{control?.regime.replaceAll("_", " ") ?? "NORMAL"}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Portfolio Volatility</p>
          <p className="mt-2 text-lg font-semibold">{control ? percent(control.volatility_state) : "—"}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Composite Risk</p>
          <p className="mt-2 text-lg font-semibold">{risk ? risk.risk_state.replaceAll("_", " ") : "—"}</p>
          <p className="mt-1 text-xs text-slate-500">score {risk?.composite_score.toFixed(2)}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">As of</p>
          <p className="mt-2 text-lg font-semibold">{formatDate(result.as_of_date)}</p>
        </div>
      </div>
    </Panel>
  )
}

function SignalAndReliability({ result }: { result: NonNullable<ReturnType<typeof readLatestEvaluation>> }) {
  const control = result.controls[0]
  const direction = control?.direction ?? "—"
  return (
    <Panel>
      <PanelHeader title="Signal & Reliability" />
      <div className="p-6">
        <div className="flex items-center justify-between rounded-lg bg-slate-950 px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Portfolio Signal</p>
            <p className="mt-1 text-xl font-semibold text-white">{direction.replaceAll("_", " ")}</p>
          </div>
          <span className={cn("rounded-full px-3 py-1 text-xs font-bold", direction === "HOLD" ? "bg-emerald-500/20 text-emerald-300" : direction === "ADAPT" ? "bg-amber-500/20 text-amber-300" : "bg-sky-500/20 text-sky-300")}>{direction}</span>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Reliability</p>
            <p className="mt-1 text-lg font-semibold">{control?.reliability_state ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Composite Risk</p>
            <p className="mt-1 text-lg font-semibold">{result.composite_risk ? result.composite_risk.composite_score.toFixed(2) : "—"}</p>
          </div>
        </div>

        {result.composite_risk && (
          <div className="mt-5">
            <p className="text-xs uppercase tracking-wide text-slate-500">Risk components</p>
            <div className="mt-2 space-y-2">
              <ComponentBar label="Volatility exposure" value={result.composite_risk.components.volatility_exposure} />
              <ComponentBar label="Concentration" value={result.composite_risk.components.concentration} />
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}

function ComponentBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-36 shrink-0 text-sm text-slate-600">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(value * 100, 100)}%` }} />
      </div>
      <span className="w-12 text-right text-sm font-semibold tabular-nums">{value.toFixed(2)}</span>
    </div>
  )
}

function DecisionNarrative({ result, portfolioValue, holdings }: { result: NonNullable<ReturnType<typeof readLatestEvaluation>>; portfolioValue: number; holdings: Array<{ ticker: string; current_price: number; market_value: number }> }) {
  const decision = result.allocation_result?.decision ?? "HOLD"
  const isRebalance = decision === "REBALANCE_REQUIRED"
  const orders = previewOrders(result, holdings)
  const turnover = previewTurnover(result)

  return (
    <Panel>
      <PanelHeader title="Veyra Control Assessment" subtitle="The portfolio's current market, risk and signal conditions were combined to determine the appropriate allocation response." />
      <div className="p-6">
        <div className={cn("rounded-xl border p-6 text-center", isRebalance ? "border-amber-200 bg-amber-50" : "border-emerald-200 bg-emerald-50")}>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Decision</p>
          <h3 className={cn("mt-2 text-3xl font-semibold tracking-tight", isRebalance ? "text-amber-900" : "text-emerald-800")}>{isRebalance ? "Rebalance required" : "Hold"}</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-600">
            {isRebalance ? "Veyra detected meaningful allocation changes supported by current conditions." : "Current conditions do not require an allocation adjustment."}
          </p>
        </div>

        {result.allocation_result && (
          <div className="mt-6">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Current → Target</h4>
              <span className="text-sm text-slate-500">Estimated turnover {percent(turnover)}</span>
            </div>
            <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr><th className="px-4 py-2.5 font-semibold">Asset</th><th className="px-4 py-2.5 text-right font-semibold">Current</th><th className="px-4 py-2.5 text-right font-semibold">Target</th><th className="px-4 py-2.5 text-right font-semibold">Change</th></tr>
                </thead>
                <tbody>
                  {result.allocation_result.allocations.map((alloc) => (
                    <tr key={alloc.ticker} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3 font-semibold">{alloc.ticker}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-600">{percent(alloc.current_weight)}</td>
                      <td className="px-4 py-3 text-right tabular-nums font-medium">{percent(alloc.target_weight)}</td>
                      <td className={cn("px-4 py-3 text-right font-semibold tabular-nums", alloc.delta_weight > 0 ? "text-emerald-700" : alloc.delta_weight < 0 ? "text-red-600" : "text-slate-400")}>{signedPercent(alloc.delta_weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-400">Portfolio value {currency(portfolioValue)}</p>
          </div>
        )}

        <div className="mt-6 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
          Veyra keeps the underlying methodology — GARCH volatility, signal attenuation, reliability weighting, composite risk and constrained optimization — beneath the surface. Here you see only the conclusion and the proposed change.
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/app/evaluation/rebalance" className={cn("inline-flex h-11 items-center justify-center rounded-lg px-5 text-sm font-semibold text-white transition-colors", isRebalance ? "bg-amber-600 hover:bg-amber-700" : "bg-emerald-600 hover:bg-emerald-700")}>
            Review Rebalance
          </Link>
          {(orders?.length ?? 0) === 0 && !isRebalance && (
            <button onClick={() => window.location.reload()} className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-300 px-5 text-sm font-semibold text-slate-800 hover:bg-slate-50">Re-run</button>
          )}
        </div>
      </div>
    </Panel>
  )
}