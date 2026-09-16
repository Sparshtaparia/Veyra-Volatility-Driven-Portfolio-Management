import { useState } from "react"
import { LoaderCircle, Plus, RefreshCw, ShieldCheck } from "lucide-react"
import { useAuth } from "@/auth/auth-context"
import { getSavedPortfolioId, useAddHolding, useCreatePortfolio, useEvaluatePortfolio, useHoldings, usePortfolio, useExecuteRebalance } from "@/hooks/use-portfolio"
import type { SignalDecision } from "@/api/portfolios"

const currency = (value: number, code = "INR") => new Intl.NumberFormat("en-IN", { style: "currency", currency: code, maximumFractionDigits: 0 }).format(value)

export function InvestorDashboardPage() {
  const { user } = useAuth(); const [portfolioId, setPortfolioId] = useState(getSavedPortfolioId)
  const portfolio = usePortfolio(portfolioId); const holdings = useHoldings(portfolioId); const createPortfolio = useCreatePortfolio(); const addHolding = useAddHolding(portfolioId); const evaluate = useEvaluatePortfolio(portfolioId)
  if (!portfolioId) return <NewPortfolio onCreate={(name) => createPortfolio.mutate({ name, currency: "INR" }, { onSuccess: (created) => setPortfolioId(created.portfolio_id) })} pending={createPortfolio.isPending} error={createPortfolio.error?.message} />
  return <main className="min-h-screen bg-slate-50 px-5 py-8 sm:px-8"><div className="mx-auto max-w-6xl"><header className="flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm font-semibold text-emerald-700">INVESTOR WORKSPACE</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Good to see you, {user?.name}</h1><p className="mt-2 text-slate-600">Veyra translates your portfolio state into practical decision guidance.</p></div><button onClick={() => evaluate.mutate()} disabled={evaluate.isPending || !portfolio.data} className="inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white disabled:opacity-60"><RefreshCw className={evaluate.isPending ? "size-4 animate-spin" : "size-4"} /> Evaluate portfolio</button></header>{(portfolio.error || holdings.error || evaluate.error) && <Notice text={(portfolio.error ?? holdings.error ?? evaluate.error)?.message ?? "Unable to load the portfolio."} />}{portfolio.isLoading ? <Loading /> : portfolio.data && <><section className="mt-8 grid gap-4 sm:grid-cols-3"><Metric label="Portfolio value" value={currency(portfolio.data.total_value, portfolio.data.currency)} /><Metric label="Holdings" value={String(holdings.data?.length ?? 0)} /><Metric label="Portfolio status" value="Ready to evaluate" /></section><section className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_.6fr]"><div className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-semibold">Your holdings</h2>{holdings.isLoading ? <Loading /> : holdings.data?.length ? <div className="mt-5 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b text-slate-500"><tr><th className="pb-3">Ticker</th><th className="pb-3">Quantity</th><th className="pb-3">Value</th><th className="pb-3">Weight</th></tr></thead><tbody>{holdings.data.map((holding) => <tr key={holding.id} className="border-b border-slate-100"><td className="py-4 font-semibold">{holding.ticker}</td><td>{holding.quantity}</td><td>{currency(holding.market_value, portfolio.data.currency)}</td><td>{(holding.weight * 100).toFixed(1)}%</td></tr>)}</tbody></table></div> : <p className="mt-5 text-sm text-slate-600">Add a holding to begin.</p>}</div><HoldingForm onAdd={(input) => addHolding.mutate(input)} pending={addHolding.isPending} error={addHolding.error?.message} /></section>{evaluate.data && <DecisionSummary result={evaluate.data} portfolioId={portfolioId} />}</>}</div></main>
}

function DecisionSummary({ result, portfolioId }: { result: SignalDecision, portfolioId: string }) { 
  const executeRebalance = useExecuteRebalance(portfolioId);
  return <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6"><div className="flex items-center justify-between"><p className="text-sm font-semibold text-emerald-700">PORTFOLIO DECISION</p>{result.allocation_result && <span className={`rounded-full px-3 py-1 text-xs font-bold ${result.allocation_result.decision === "REBALANCE_REQUIRED" ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900"}`}>{result.allocation_result.decision.replace("_", " ")}</span>}</div><div className="flex justify-between items-end"><h2 className="mt-2 text-xl font-semibold">Current signal controls</h2>{result.composite_risk && <div className="text-right"><p className="text-xs text-slate-500 uppercase tracking-wide">Composite Risk</p><p className="text-sm font-semibold text-slate-900">{result.composite_risk.risk_state.replaceAll("_", " ")} ({(result.composite_risk.composite_score * 100).toFixed(1)}%)</p><p className="text-xs text-slate-500">Vol Exp: {(result.composite_risk.components.volatility_exposure * 100).toFixed(1)}% · Conc: {(result.composite_risk.components.concentration * 100).toFixed(1)}%</p></div>}</div><div className="mt-4 space-y-3">{result.controls.map((item) => <article key={item.ticker} className="rounded-lg bg-slate-50 p-4"><div className="flex items-center justify-between gap-3"><strong>{item.ticker}</strong><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">{item.decision_state}</span></div><p className="mt-2 text-sm text-slate-600">{item.regime.replaceAll("_", " ")} · vol {item.volatility_state.toFixed(3)} · reliability {item.reliability_state} · base {item.base_signal.toFixed(2)} → reg {item.regulated_signal.toFixed(2)} → ctrl {item.control_output.toFixed(2)}</p><p className="mt-1 text-sm text-slate-700">{item.reason_codes.join(" · ").replaceAll("_", " ")}</p></article>)}</div>{result.allocation_result && <div className="mt-8"><h3 className="text-lg font-semibold border-t pt-6">Target Allocations</h3><p className="text-sm text-slate-600">Turnover: {(result.allocation_result.total_turnover * 100).toFixed(1)}%</p><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b text-slate-500"><tr><th className="pb-3">Ticker</th><th className="pb-3 text-right">Current Weight</th><th className="pb-3 text-right">Target Weight</th><th className="pb-3 text-right">Change</th></tr></thead><tbody>{result.allocation_result.allocations.map(a => <tr key={a.ticker} className="border-b border-slate-100"><td className="py-4 font-semibold">{a.ticker}</td><td className="text-right">{(a.current_weight * 100).toFixed(1)}%</td><td className="text-right font-medium">{(a.target_weight * 100).toFixed(1)}%</td><td className={`text-right ${a.delta_weight > 0 ? "text-emerald-600" : a.delta_weight < 0 ? "text-red-600" : ""}`}>{a.delta_weight > 0 ? "+" : ""}{(a.delta_weight * 100).toFixed(1)}%</td></tr>)}</tbody></table></div>
  
  {result.allocation_result.decision === "HOLD" ? (
    <p className="mt-6 font-semibold text-slate-700">No rebalancing required.</p>
  ) : (
    <div className="mt-6 border-t pt-6">
      <div className="rounded-lg bg-amber-50 p-4 border border-amber-200">
        <h4 className="font-semibold text-amber-900">Execute Paper Rebalance</h4>
        <p className="mt-1 text-sm text-amber-800">
          This is a SIMULATION. It will generate paper orders and simulate the portfolio update without modifying your real holdings.
        </p>
        <button 
          onClick={() => executeRebalance.mutate()}
          disabled={executeRebalance.isPending}
          className="mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 text-sm font-semibold text-white shadow-sm disabled:opacity-50"
        >
          {executeRebalance.isPending ? "Simulating execution..." : "Execute Paper Rebalance"}
        </button>
      </div>
      
      {executeRebalance.error && <Notice text={executeRebalance.error.message} />}
      
      {executeRebalance.data && (
        <div className="mt-6 rounded-lg border border-slate-200 p-5">
          <h4 className="font-semibold flex items-center gap-2 text-emerald-700">
            <ShieldCheck className="size-5" /> Execution Complete
          </h4>
          <p className="text-sm text-slate-600 mt-1">Total Cost / Slippage: {currency(executeRebalance.data.total_cost)}</p>
          
          <h5 className="mt-4 text-sm font-semibold uppercase text-slate-500 tracking-wide">Paper Orders</h5>
          <div className="mt-2 space-y-2">
            {executeRebalance.data.orders.map((o: any, i: number) => (
              <div key={i} className="flex justify-between items-center text-sm border-b pb-2">
                <div>
                  <span className={`font-bold mr-2 ${o.side === 'BUY' ? 'text-emerald-600' : 'text-red-600'}`}>{o.side}</span>
                  <span className="font-medium">{o.ticker}</span>
                  <span className="ml-2 text-slate-500">{o.quantity.toFixed(4)} @ {currency(o.execution_price)}</span>
                </div>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{o.status}</span>
              </div>
            ))}
          </div>

          <h5 className="mt-6 text-sm font-semibold uppercase text-slate-500 tracking-wide">Simulated Portfolio State</h5>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b text-slate-500">
                <tr><th className="pb-2">Ticker</th><th className="pb-2 text-right">Quantity</th><th className="pb-2 text-right">Simulated Weight</th></tr>
              </thead>
              <tbody>
                {executeRebalance.data.simulated_holdings.map((h: any, i: number) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 font-medium">{h.ticker}</td>
                    <td className="py-2 text-right">{h.quantity.toFixed(4)}</td>
                    <td className="py-2 text-right font-semibold text-emerald-700">{(h.weight * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )}
  </div>}</section> }
function NewPortfolio({ onCreate, pending, error }: { onCreate: (name: string) => void; pending: boolean; error?: string }) { const [name, setName] = useState(""); return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-7"><ShieldCheck className="size-8 text-emerald-700" /><h1 className="mt-5 text-2xl font-semibold">Create your first portfolio</h1><form className="mt-6" onSubmit={(event) => { event.preventDefault(); if (name.trim()) onCreate(name.trim()) }}><input required value={name} onChange={(event) => setName(event.target.value)} placeholder="My long-term investments" className="h-11 w-full rounded-lg border border-slate-300 px-3" />{error && <Notice text={error} />}<button disabled={pending} className="mt-5 h-11 w-full rounded-lg bg-slate-950 text-sm font-semibold text-white">Create portfolio</button></form></div></main> }
function HoldingForm({ onAdd, pending, error }: { onAdd: (input: { ticker: string; quantity: number; average_price: number; current_price: number }) => void; pending: boolean; error?: string }) { const [ticker, setTicker] = useState(""); const [quantity, setQuantity] = useState(""); const [price, setPrice] = useState(""); return <form onSubmit={(event) => { event.preventDefault(); onAdd({ ticker: ticker.toUpperCase(), quantity: Number(quantity), average_price: Number(price), current_price: Number(price) }); setTicker(""); setQuantity(""); setPrice("") }} className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-semibold">Add a holding</h2><div className="mt-5 space-y-3"><Input value={ticker} onChange={setTicker} placeholder="Ticker" /><Input value={quantity} onChange={setQuantity} placeholder="Quantity" type="number" /><Input value={price} onChange={setPrice} placeholder="Average/current price" type="number" /></div>{error && <Notice text={error} />}<button disabled={pending} className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-slate-300 text-sm font-semibold"><Plus className="size-4" /> {pending ? "Saving…" : "Save holding"}</button></form> }
function Input({ value, onChange, placeholder, type = "text" }: { value: string; onChange: (value: string) => void; placeholder: string; type?: string }) { return <input required type={type} min={type === "number" ? "0" : undefined} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-10 w-full rounded-lg border border-slate-300 px-3" /> }
function Metric({ label, value }: { label: string; value: string }) { return <article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></article> }
function Loading() { return <p className="mt-5 flex gap-2 text-sm text-slate-600"><LoaderCircle className="size-4 animate-spin" /> Loading…</p> }
function Notice({ text }: { text: string }) { return <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{text}</p> }
