import { useState } from "react"
import { ArrowLeft, ShieldCheck } from "lucide-react"
import { Link } from "react-router-dom"
import { useExecuteRebalance, useHoldings, usePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { readLatestEvaluation, readLatestExecution, writeLatestExecution, type PaperExecutionResult } from "@/lib/evaluation-store"
import { previewOrders, previewTurnover } from "@/lib/rebalance-preview"
import { currency, percent, signedPercent } from "@/lib/format"
import { Badge, EmptyState, Loading, Notice, Panel, PanelHeader } from "@/components/ui/primitives"
import { cn } from "cn"

export function RebalanceReviewPage() {
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const executeRebalance = useExecuteRebalance(portfolioId)
  const [execution, setExecution] = useState<PaperExecutionResult | null>(() => (portfolioId ? readLatestExecution(portfolioId) : null))

  const result = portfolioId ? readLatestEvaluation(portfolioId) : null
  const decision = result?.allocation_result?.decision
  const isRebalance = decision === "REBALANCE_REQUIRED"

  function run() {
    if (!portfolioId) return
    executeRebalance.mutate(undefined, {
      onSuccess: (value) => {
        writeLatestExecution(portfolioId, value)
        setExecution(value)
      },
    })
  }

  if (!portfolioId || !portfolio.data) {
    return <EmptyState title="Nothing to review" text="Create a portfolio before reviewing a rebalance." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />
  }

  if (holdings.isLoading) return <Loading label="Loading portfolio…" />

  if (!result || !isRebalance) {
    return (
      <Panel className="mx-auto mt-10 max-w-lg">
        <EmptyState
          title="No rebalance required"
          text="Run an evaluation first. If Veyra detects meaningful allocation changes, the recommended shift will appear here for review."
          action={<Link to="/app/evaluation" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Go to Evaluation</Link>}
        />
      </Panel>
    )
  }

  const orders = previewOrders(result, holdings.data ?? [])
  const turnover = previewTurnover(result)
  const totalNotional = orders?.reduce((sum, o) => sum + Math.abs(o.notional), 0) ?? 0
  const totalValue = portfolio.data.total_value

  if (execution) {
    return (
      <div className="mx-auto max-w-4xl">
        <ExecutionResult execution={execution} onReset={() => setExecution(null)} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/app/evaluation" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950"><ArrowLeft className="size-4" /> Back to evaluation</Link>

      <header className="mt-4">
        <p className="text-sm font-semibold text-emerald-700">REBALANCE</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Review Rebalance</h1>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">Veyra recommends the following portfolio changes. This is a preview — no trades have been placed.</p>
      </header>

      {executeRebalance.error && <Notice text={executeRebalance.error.message} />}

      <section className="mt-6 grid gap-6 md:grid-cols-2">
        <Panel>
          <PanelHeader title="Buy" />
          <div className="space-y-4 p-6">
            {orders?.filter((o) => o.side === "BUY").length ? (
              orders.filter((o) => o.side === "BUY").map((order) => (
                <div key={order.ticker} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{order.ticker}</p>
                    <p className="text-sm text-slate-500">{signedPercent(order.weightChange)} → {currency(order.notional)}</p>
                  </div>
                  <Badge tone="emerald">BUY</Badge>
                </div>
              ))
            ) : <p className="text-sm text-slate-500">No buys required.</p>}
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="Sell" />
          <div className="space-y-4 p-6">
            {orders?.filter((o) => o.side === "SELL").length ? (
              orders.filter((o) => o.side === "SELL").map((order) => (
                <div key={order.ticker} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{order.ticker}</p>
                    <p className="text-sm text-slate-500">{signedPercent(order.weightChange)} → {currency(Math.abs(order.notional))}</p>
                  </div>
                  <Badge tone="red">SELL</Badge>
                </div>
              ))
            ) : <p className="text-sm text-slate-500">No sells required.</p>}
          </div>
        </Panel>
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <SummaryItem label="Estimated Turnover" value={percent(Math.min(turnover, 1))} />
        <SummaryItem label="Total Notional" value={currency(totalNotional)} />
        <SummaryItem label="Portfolio Value" value={currency(totalValue)} />
      </section>

      <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="font-semibold text-amber-900">Paper execution only</p>
        <p className="mt-1 text-sm leading-6 text-amber-800">No real trades will be placed. Executing this rebalance creates a simulated order plan and an estimated portfolio state. Your actual holdings are never modified.</p>
        <button onClick={run} disabled={executeRebalance.isPending} className="mt-4 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-amber-600 px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-700 disabled:opacity-60">
          <ShieldCheck className="size-4" /> {executeRebalance.isPending ? "Simulating execution…" : "Execute Paper Rebalance"}
        </button>
      </section>
    </div>
  )
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-xl font-semibold tracking-tight">{value}</p></div>
}

function ExecutionResult({ execution, onReset }: { execution: PaperExecutionResult; onReset: () => void }) {
  const before = Object.fromEntries((execution.simulated_holdings ?? []).map((h) => [h.ticker.toUpperCase(), h.weight]))
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center">
        <p className="mx-auto grid size-14 place-items-center rounded-full bg-emerald-600 text-white"><ShieldCheck className="size-7" /></p>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight">Paper Rebalance Completed</h1>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-emerald-900">Your simulated order plan was generated and marked as filled on the paper account.</p>
      </section>

      <Panel>
        <PanelHeader title="Orders" subtitle={`${execution.orders.length} orders · ${currency(execution.total_cost)} total cost`} />
        <div className="divide-y divide-slate-100 px-6">
          {execution.orders.map((order, index) => (
            <div key={index} className="flex items-center justify-between gap-4 py-3.5">
              <div className="flex items-center gap-3">
                <span className={cn("w-14 rounded-full px-2 py-1 text-center text-xs font-bold", order.side === "BUY" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800")}>{order.side}</span>
                <div>
                  <p className="text-sm font-semibold">{order.ticker}</p>
                  <p className="text-xs text-slate-500">{order.quantity.toFixed(4)} @ {currency(order.execution_price)}</p>
                </div>
              </div>
              <Badge tone="emerald">FILLED</Badge>
            </div>
          ))}
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Simulated Portfolio" subtitle="Before vs after — paper estimate only" />
        <div className="overflow-x-auto px-6 py-4">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="pb-3 font-semibold">Asset</th><th className="pb-3 text-right font-semibold">Before</th><th className="pb-3 text-right font-semibold">After</th></tr>
            </thead>
            <tbody>
              {execution.simulated_holdings.map((h) => {
                const prev = before[h.ticker.toUpperCase()]
                const diff = prev != null ? h.weight - prev : null
                return (
                  <tr key={h.ticker} className="border-b border-slate-100 last:border-0">
                    <td className="py-3 font-semibold">{h.ticker}</td>
                    <td className="py-3 text-right tabular-nums text-slate-600">{prev != null ? percent(prev) : "—"}</td>
                    <td className="py-3 text-right font-semibold tabular-nums">{percent(h.weight)} {diff != null && diff > 0.0001 && <span className="ml-1 text-xs font-semibold text-emerald-600">↑</span>}{diff != null && diff < -0.0001 && <span className="ml-1 text-xs font-semibold text-red-600">↓</span>}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="border-t border-slate-100 px-6 py-4">
          <p className="text-xs leading-5 text-slate-500">This is a simulated portfolio state. Your actual holdings were not changed.</p>
          <button onClick={onReset} className="mt-4 inline-flex h-10 items-center justify-center rounded-lg border border-slate-300 px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50">Close result</button>
        </div>
      </Panel>
    </div>
  )
}