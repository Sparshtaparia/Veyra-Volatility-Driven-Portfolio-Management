import { useState } from "react"
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Info,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Zap,
  ArrowUp,
  ArrowDown,
  Minus,
} from "lucide-react"
import { Link } from "react-router-dom"
import { InvestorShell } from "@/components/layout/investor-shell"
import {
  getSavedPortfolioId,
  useEvaluatePortfolio,
  useExecuteRebalance,
  useHoldings,
  usePortfolio,
} from "@/hooks/use-portfolio"
import { SkeletonCard, SkeletonStatCard } from "@/components/common/skeleton"

// ─── Helpers ──────────────────────────────────────────────────────────────

const INR = (v: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v)
const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const humanize = (v: string) => v.replaceAll("_", " ").replace(/\b\w/g, (l) => l.toUpperCase())

const COLOURS = ["#16a34a", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899"]

// ─── Step pill ────────────────────────────────────────────────────────────

function StepPill({ n, label, active, done }: { n: number; label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`grid size-7 place-items-center rounded-full text-xs font-bold transition-colors ${
        done ? "bg-emerald-600 text-white" :
        active ? "bg-slate-950 text-white" :
        "bg-slate-200 text-slate-500"
      }`}>
        {done ? "✓" : n}
      </span>
      <span className={`text-sm font-medium ${active ? "text-slate-900" : "text-slate-400"}`}>{label}</span>
    </div>
  )
}

// ─── Allocation row ────────────────────────────────────────────────────────

function AllocationRow({ ticker, current, target, delta, colour }: {
  ticker: string; current: number; target: number; delta: number; colour: string
}) {
  const isUp   = delta > 0.005
  const isDown = delta < -0.005
  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50 transition">
      <td className="px-5 py-3.5">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full" style={{ background: colour }} />
          <span className="font-semibold text-slate-900">{ticker}</span>
        </div>
      </td>
      <td className="px-4 py-3.5 text-right tabular-nums text-slate-600">{pct(current)}</td>
      <td className="px-4 py-3.5 text-right tabular-nums text-slate-600">{pct(target)}</td>
      <td className="px-5 py-3.5 text-right font-semibold">
        {isUp   ? <span className="text-emerald-600 inline-flex items-center gap-1"><ArrowUp   className="size-3" />{pct(Math.abs(delta))}</span> :
         isDown  ? <span className="text-rose-600    inline-flex items-center gap-1"><ArrowDown className="size-3" />{pct(Math.abs(delta))}</span> :
                   <span className="text-slate-400   inline-flex items-center gap-1"><Minus     className="size-3" />0%</span>}
      </td>
    </tr>
  )
}

// ─── Order card ───────────────────────────────────────────────────────────

function OrderCard({ order, i }: { order: any; i: number }) {
  const isBuy = order.side === "BUY"
  return (
    <div className={`flex items-center justify-between rounded-xl border px-4 py-3.5 animate-fade-up ${isBuy ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"}`}
      style={{ animationDelay: `${i * 60}ms` }}>
      <div className="flex items-center gap-3">
        <span className={`grid size-8 place-items-center rounded-full text-xs font-bold text-white ${isBuy ? "bg-emerald-600" : "bg-rose-600"}`}>
          {order.ticker[0]}
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-900">{order.ticker}</p>
          <p className="text-xs text-slate-500">{humanize(order.side)} {order.quantity} units @ {INR(order.execution_price)}</p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-bold ${isBuy ? "text-rose-600" : "text-emerald-600"}`}>
          {isBuy ? "−" : "+"}{INR(Math.abs(order.quantity * order.execution_price))}
        </p>
        <p className="text-[11px] text-slate-400">cost: {INR(order.transaction_cost ?? 0)}</p>
      </div>
    </div>
  )
}

// ─── Why section ──────────────────────────────────────────────────────────

function WhySection({ decision }: { decision?: string }) {
  const isHold = !decision || decision === "HOLD"
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Info className="size-4 text-amber-600" />
        <p className="font-semibold text-slate-900">Why this recommendation?</p>
      </div>
      <ul className="space-y-3">
        {isHold ? (
          <>
            <li className="flex gap-3"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" /><div><p className="text-sm font-semibold text-slate-900">Portfolio within thresholds</p><p className="text-xs text-slate-500">All holdings are within risk bounds.</p></div></li>
            <li className="flex gap-3"><ShieldCheck   className="mt-0.5 size-4 shrink-0 text-emerald-600" /><div><p className="text-sm font-semibold text-slate-900">Stable market regime</p><p className="text-xs text-slate-500">No significant volatility spikes detected.</p></div></li>
          </>
        ) : (
          <>
            <li className="flex gap-3"><AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" /><div><p className="text-sm font-semibold text-slate-900">Allocation drift detected</p><p className="text-xs text-slate-500">Holdings have drifted from target weights.</p></div></li>
            <li className="flex gap-3"><RefreshCw     className="mt-0.5 size-4 shrink-0 text-blue-600"  /><div><p className="text-sm font-semibold text-slate-900">Rebalancing will reduce risk</p><p className="text-xs text-slate-500">Trading back to target reduces composite risk score.</p></div></li>
            <li className="flex gap-3"><ShieldCheck   className="mt-0.5 size-4 shrink-0 text-slate-500" /><div><p className="text-sm font-semibold text-slate-900">Risk discipline maintained</p><p className="text-xs text-slate-500">Aligned with your adaptive volatility threshold.</p></div></li>
          </>
        )}
      </ul>
    </div>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────

type Phase = "idle" | "evaluated" | "executed"

export function RebalanceReviewPage() {
  const portfolioId = getSavedPortfolioId()
  const portfolio   = usePortfolio(portfolioId)
  const holdings    = useHoldings(portfolioId)
  const evaluate    = useEvaluatePortfolio(portfolioId)
  const rebalance   = useExecuteRebalance(portfolioId)
  const [phase, setPhase] = useState<Phase>("idle")

  const allocation = evaluate.data?.allocation_result
  const decision   = allocation?.decision
  const isHold     = !decision || decision === "HOLD"
  const orders     = rebalance.data?.orders ?? []
  const totalCost  = rebalance.data?.total_cost ?? 0

  return (
    <InvestorShell>
      <div className="px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="size-5 text-emerald-600" />
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Triggers</p>
            </div>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-900">Rebalance Review</h1>
            <p className="mt-1 text-sm text-slate-500">
              Analyse your portfolio and simulate the recommended rebalancing. No real trades are executed.
            </p>
          </div>
          <Link to="/app/evaluation" className="shrink-0 inline-flex h-10 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition">
            View Evaluation →
          </Link>
        </div>

        {/* Step progress */}
        <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <StepPill n={1} label="Analyse Portfolio"     active={phase === "idle"}     done={phase !== "idle"} />
          <ArrowRight className="size-4 text-slate-300 hidden sm:block" />
          <StepPill n={2} label="Review Recommendation" active={phase === "evaluated"} done={phase === "executed"} />
          <ArrowRight className="size-4 text-slate-300 hidden sm:block" />
          <StepPill n={3} label="Simulate Rebalance"    active={phase === "executed"} done={false} />
        </div>

        {!portfolioId ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
            No portfolio found. <Link to="/app/portfolio" className="font-semibold text-emerald-700 hover:underline">Create one</Link>.
          </div>
        ) : (
          <>
            {/* Step 1: Run evaluation */}
            {phase === "idle" && (
              <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm animate-fade-up">
                <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
                  <Zap className="size-7" />
                </span>
                <p className="mt-4 text-lg font-bold text-slate-900">Start with an evaluation</p>
                <p className="mt-1.5 text-sm leading-6 text-slate-500 max-w-sm mx-auto">
                  Veyra will assess current market conditions, compute signals for each holding,
                  and determine whether a rebalance is needed.
                </p>
                <button
                  onClick={() => evaluate.mutate(undefined, { onSuccess: () => setPhase("evaluated") })}
                  disabled={evaluate.isPending}
                  className="mt-6 inline-flex h-11 items-center gap-2 rounded-xl bg-slate-950 px-6 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
                >
                  {evaluate.isPending
                    ? <><LoaderCircle className="size-4 animate-spin" /> Evaluating…</>
                    : <><Play className="size-4 fill-white" /> Analyse Now</>}
                </button>
              </div>
            )}

            {/* Step 2: Show recommendation */}
            {phase === "evaluated" && (
              <>
                <div className={`rounded-xl border p-5 shadow-sm animate-fade-up ${isHold ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
                  <div className="flex items-center gap-3">
                    {isHold
                      ? <CheckCircle2 className="size-6 shrink-0 text-emerald-600" />
                      : <AlertTriangle className="size-6 shrink-0 text-amber-600" />}
                    <div className="flex-1">
                      <p className={`text-base font-bold ${isHold ? "text-emerald-900" : "text-amber-900"}`}>
                        {isHold ? "No rebalance needed" : "Rebalance recommended"}
                      </p>
                      <p className={`mt-0.5 text-sm ${isHold ? "text-emerald-700" : "text-amber-700"}`}>
                        {isHold
                          ? "Your portfolio is well-aligned with current market conditions."
                          : "Meaningful allocation drift detected. Simulating rebalance is advised."}
                      </p>
                    </div>
                    {!isHold && (
                      <button
                        onClick={() => rebalance.mutate(undefined, { onSuccess: () => setPhase("executed") })}
                        disabled={rebalance.isPending}
                        className="shrink-0 inline-flex h-10 items-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
                      >
                        {rebalance.isPending
                          ? <><LoaderCircle className="size-4 animate-spin" /> Simulating…</>
                          : <><RefreshCw className="size-4" /> Simulate Rebalance</>}
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    { label: "Portfolio Value", value: INR(portfolio.data?.total_value ?? 0) },
                    { label: "Total Holdings",  value: String(holdings.data?.length ?? "—") },
                    { label: "Total Turnover",  value: allocation ? pct(allocation.total_turnover) : "—" },
                    { label: "Decision",        value: humanize(decision ?? "Unknown") },
                  ].map((c) => (
                    <div key={c.label} className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm animate-fade-up">
                      <p className="text-xs text-slate-500">{c.label}</p>
                      <p className="mt-1 text-xl font-black text-slate-900 tabular-nums">{c.value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-100 px-5 py-4">
                      <p className="text-sm font-semibold text-slate-900">Allocation Comparison</p>
                      <p className="text-xs text-slate-500">Current vs. recommended target weights</p>
                    </div>
                    {allocation?.allocations?.length ? (
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[420px] text-sm">
                          <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                            <tr>
                              <th className="px-5 py-3 text-left">Asset</th>
                              <th className="px-4 py-3 text-right">Current</th>
                              <th className="px-4 py-3 text-right">Target</th>
                              <th className="px-5 py-3 text-right">Change</th>
                            </tr>
                          </thead>
                          <tbody>
                            {allocation.allocations.map((a, i) => (
                              <AllocationRow key={a.ticker} ticker={a.ticker} current={a.current_weight} target={a.target_weight} delta={a.delta_weight} colour={COLOURS[i % COLOURS.length]} />
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="px-5 py-8 text-sm text-slate-400 text-center">No allocation data.</p>
                    )}
                  </div>
                  <WhySection decision={decision} />
                </div>

                {isHold && (
                  <div className="flex justify-center">
                    <button onClick={() => setPhase("idle")} className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition">
                      <RefreshCw className="size-3.5" /> Re-run evaluation
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Step 3: Simulated orders */}
            {phase === "executed" && (
              <>
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm animate-fade-up">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="size-6 shrink-0 text-emerald-600" />
                    <div>
                      <p className="font-bold text-emerald-900">Simulation complete</p>
                      <p className="text-sm text-emerald-700">
                        {orders.length} orders simulated. Total simulated cost: <strong>{INR(totalCost)}</strong>.
                        No real trades have been executed.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
                  <div>
                    <p className="mb-3 text-sm font-semibold text-slate-900">Simulated Orders</p>
                    <div className="space-y-2">
                      {orders.length ? orders.map((o, i) => <OrderCard key={i} order={o} i={i} />) : (
                        <p className="text-sm text-slate-400">No orders returned.</p>
                      )}
                    </div>
                  </div>
                  <WhySection decision={evaluate.data?.allocation_result?.decision} />
                </div>

                <div className="flex justify-center gap-3">
                  <button onClick={() => setPhase("idle")} className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition">
                    <RefreshCw className="size-3.5" /> Start over
                  </button>
                  <Link to="/app/portfolio" className="inline-flex h-9 items-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 transition">
                    View Portfolio →
                  </Link>
                </div>
              </>
            )}

            {/* Disclaimer */}
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-xs text-slate-500 shadow-sm">
              <Info className="size-4 shrink-0 text-emerald-600" />
              This is a simulated paper rebalance. No real trades are executed. Values shown are based on current prices.
            </div>
          </>
        )}
      </div>
    </InvestorShell>
  )
}