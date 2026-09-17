import { Link } from "react-router-dom"
import { useAnalyticsDashboard, useHoldings } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { currency, percent, signedPercent } from "@/lib/format"
import { Badge, EmptyState, Loading, Notice, Panel, PanelHeader } from "@/components/ui/primitives"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts"

const COLORS = ['#0f172a', '#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1']

export function AnalyticsPage() {
  const portfolioId = getSavedPortfolioId()
  const dashboard = useAnalyticsDashboard(portfolioId)
  const holdingsQuery = useHoldings(portfolioId)

  if (!portfolioId) return <EmptyState title="No analytics yet" text="Create a portfolio to see performance and risk analytics." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />

  if (dashboard.isLoading || holdingsQuery.isLoading) return <Loading label="Loading analytics dashboard…" />
  if (dashboard.error) return <Notice text={dashboard.error.message} />
  if (!dashboard.data) return <Notice text="No data available" />

  const data = dashboard.data
  const p = data.performance
  const r = data.risk_assessment
  const c = data.concentration
  
  const pieData = (holdingsQuery.data ?? [])
    .filter(h => h.weight > 0)
    .sort((a, b) => b.weight - a.weight)
    .map(h => ({ name: h.ticker, value: h.weight }))

  return (
    <div className="mx-auto max-w-5xl space-y-12 pb-24">
      <header>
        <p className="text-sm font-semibold text-emerald-700">ANALYTICS</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Performance & Risk</h1>
        <p className="mt-2 text-sm text-slate-500 max-w-2xl">
          An explainable, data-driven view of your portfolio's performance, risk profile, and history. 
          Veyra strictly relies on observed database snapshots and mathematically derived risk metrics.
        </p>
      </header>

      {/* 1. Portfolio Performance */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Portfolio Performance</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard title="Portfolio Value" value={currency(p.portfolio_value)} hint={`As of ${formatDateTime(data.data_stats.last_updated)}`} />
          <MetricCard title="Invested Amount" value={currency(p.invested_amount)} hint="Total capital invested based on transactions" />
          <MetricCard title="Total Return" value={p.return_percentage != null ? signedPercent(p.return_percentage) : "—"} hint={`Absolute: ${p.absolute_return > 0 ? "+" : ""}${currency(p.absolute_return)}`} />
          <MetricCard title="Annualized Return" value="Not enough history" hint="Requires at least 1 year of history" className="text-slate-500" />
        </div>

        {/* History Chart */}
        <Panel>
          <PanelHeader title="Portfolio Value Over Time" subtitle="Based on historical portfolio snapshots" />
          <div className="p-6 h-[300px]">
            {data.performance_history.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.performance_history} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                  <YAxis tickFormatter={(val) => `₹${val/1000}k`} tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value: number) => [currency(value), "Value"]} labelStyle={{color: '#0f172a', fontWeight: 600}} />
                  <Line type="monotone" dataKey="portfolio_value" stroke="#0f172a" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <p className="font-semibold text-slate-900">Performance history is building</p>
                <p className="text-sm text-slate-500 mt-1 max-w-sm">Veyra needs multiple portfolio valuation snapshots to calculate a historical performance chart.</p>
              </div>
            )}
          </div>
        </Panel>
      </section>

      {/* 2. Risk Assessment */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Risk Assessment</h2>
        
        {r ? (
          <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
            <Panel>
              <div className="p-6">
                <p className="text-sm font-semibold text-slate-500">Overall Risk Score</p>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-4xl font-bold text-slate-900">{r.overall_score}</span>
                  <span className="text-slate-500">/ 100</span>
                  <Badge variant={r.overall_score! < 33 ? "success" : r.overall_score! < 66 ? "warning" : "danger"} className="ml-2">{r.label}</Badge>
                </div>
                
                <div className="mt-8 space-y-4">
                  {Object.values(r.components).map(comp => (
                    <div key={comp.label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-slate-700">{comp.label}</span>
                        <span className="text-slate-500">{comp.score} / 100</span>
                      </div>
                      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-slate-900 rounded-full" style={{ width: `${comp.score}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
            
            <Panel>
              <div className="p-6">
                <h3 className="font-semibold text-slate-900">Why is my risk score {r.overall_score}?</h3>
                <p className="mt-2 text-sm text-slate-600 mb-4">Your portfolio's risk score is primarily driven by:</p>
                <ul className="space-y-3">
                  {r.explanations.map((exp, i) => (
                    <li key={i} className="flex gap-3 text-sm text-slate-700">
                      <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0" />
                      {exp}
                    </li>
                  ))}
                </ul>
              </div>
            </Panel>
          </div>
        ) : (
          <Panel>
            <div className="p-8 text-center">
              <p className="font-semibold text-slate-900">Building risk profile</p>
              <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">Veyra needs an evaluation cycle to calculate a reliable composite risk score.</p>
            </div>
          </Panel>
        )}
      </section>

      {/* 3. Portfolio Risk Details */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Portfolio Risk</h2>
        
        <div className="grid gap-6 md:grid-cols-[1.5fr_1fr]">
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <MetricCard 
                title="Portfolio Volatility" 
                value={data.volatility != null ? percent(data.volatility) : "Building history"} 
                hint={data.volatility != null ? "Based on standard deviation of returns" : "Requires multiple observations"} 
                className={data.volatility == null ? "text-slate-500 !text-base" : ""}
              />
              <MetricCard 
                title="Maximum Drawdown" 
                value={data.max_drawdown != null ? signedPercent(data.max_drawdown) : "Drawdown unavailable"} 
                hint={data.max_drawdown != null ? "Largest decline from a previous peak" : "More than one valuation is required"} 
                className={data.max_drawdown == null ? "text-slate-500 !text-base" : ""}
              />
            </div>
            
            <Panel>
              <PanelHeader title="Concentration Metrics" subtitle="How concentrated is your portfolio value?" />
              <div className="p-4 grid grid-cols-3 divide-x divide-slate-100">
                <div className="px-4 text-center flex flex-col justify-between">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Largest Position</p>
                  <p className="mt-1 text-xl font-semibold text-slate-900">{c.largest_position != null ? percent(c.largest_position) : "—"}</p>
                </div>
                <div className="px-4 text-center flex flex-col justify-between">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Top 3 Holdings</p>
                  <p className="mt-1 text-xl font-semibold text-slate-900">{c.top_3 != null ? percent(c.top_3) : "—"}</p>
                </div>
                <div className="px-4 text-center flex flex-col justify-between">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">HHI</p>
                  <p className="mt-1 text-xl font-semibold text-slate-900">{c.hhi != null ? c.hhi.toFixed(3) : "—"}</p>
                </div>
              </div>
            </Panel>
          </div>
          
          <Panel>
            <PanelHeader title="Allocation" subtitle="Current weights" />
            <div className="p-4 h-[250px] flex items-center justify-center">
              {pieData.length > 0 ? (
                 <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => percent(value)} />
                    </PieChart>
                  </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500">No holdings to display.</p>
              )}
            </div>
          </Panel>
        </div>
      </section>
      
      {/* 4. Veyra Decisions */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Veyra Decisions</h2>
        <Panel>
          <PanelHeader title="Recent Rebalances" subtitle={`${data.data_stats.rebalance_evaluations} evaluations completed`} />
          <div className="overflow-x-auto">
            {data.recent_decisions.length > 0 ? (
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-100">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-4 py-3 font-semibold">Action</th>
                    <th className="px-4 py-3 font-semibold">Asset</th>
                    <th className="px-4 py-3 font-semibold">Change</th>
                    <th className="px-4 py-3 font-semibold">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.recent_decisions.map((d, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 text-slate-600">{d.date}</td>
                      <td className="px-4 py-3">
                        <Badge variant={d.action === "Increased" ? "success" : "danger"}>{d.action}</Badge>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900">{d.asset}</td>
                      <td className="px-4 py-3 text-slate-600">{d.weight_change > 0 ? "+" : ""}{percent(d.weight_change)}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs truncate max-w-[200px]">{d.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-sm text-slate-500">No rebalance executions recorded yet.</div>
            )}
          </div>
        </Panel>
      </section>

      {/* 5. Adaptive Threshold */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Adaptive Threshold</h2>
        {data.adaptive_threshold ? (
          <Panel>
             <div className="p-6 flex items-center justify-between text-center max-w-lg mx-auto">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase">Previous</p>
                  <p className="text-xl font-semibold mt-1">{percent(data.adaptive_threshold.previous)}</p>
                </div>
                <div className="text-slate-300">→</div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase">Observed</p>
                  <p className="text-xl font-semibold mt-1">{percent(data.adaptive_threshold.observed)}</p>
                </div>
                <div className="text-slate-300">→</div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase">Updated</p>
                  <p className="text-xl font-semibold mt-1">{percent(data.adaptive_threshold.updated)}</p>
                </div>
             </div>
             <div className="px-6 pb-6 text-sm text-slate-500 border-t border-slate-100 pt-4 text-center">
                Veyra adjusted the threshold by {signedPercent(data.adaptive_threshold.change)} because observed portfolio volatility shifted.
             </div>
          </Panel>
        ) : (
          <Panel>
             <div className="p-8 text-center">
               <p className="font-semibold text-slate-900">No evaluation cycles have been completed yet.</p>
               <p className="text-sm text-slate-500 mt-1">The threshold will appear here after Veyra completes its first evaluation.</p>
             </div>
          </Panel>
        )}
      </section>

      {/* 6. Benchmark */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2">Benchmark</h2>
        <Notice title="Benchmark comparison unavailable" text="Benchmarking requires historical portfolio and market-price data over the same evaluation period." />
      </section>

      {/* 7. Data Methodology */}
      <section className="mt-12 pt-8 border-t border-slate-200">
        <h3 className="text-sm font-bold text-slate-900 mb-4">Data used for this analysis</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4 text-sm">
          <div><span className="block text-slate-500">Valuations</span> <span className="font-medium text-slate-900">{data.data_stats.portfolio_valuations}</span></div>
          <div><span className="block text-slate-500">Holdings</span> <span className="font-medium text-slate-900">{data.data_stats.holdings}</span></div>
          <div><span className="block text-slate-500">Transactions</span> <span className="font-medium text-slate-900">{data.data_stats.transactions}</span></div>
          <div><span className="block text-slate-500">Evaluations</span> <span className="font-medium text-slate-900">{data.data_stats.rebalance_evaluations}</span></div>
          <div><span className="block text-slate-500">History</span> <span className="font-medium text-slate-900">{data.data_stats.history_days} days</span></div>
          <div><span className="block text-slate-500">Updated</span> <span className="font-medium text-slate-900">{formatDateTime(data.data_stats.last_updated)}</span></div>
        </div>
      </section>
    </div>
  )
}

function MetricCard({ title, value, hint, className = "" }: { title: string, value: string, hint?: string, className?: string }) {
  return (
    <Panel className="p-5 flex flex-col justify-between h-full">
      <p className="text-sm font-semibold text-slate-600">{title}</p>
      <div className="mt-2">
        <p className={`text-2xl font-bold text-slate-900 ${className}`}>{value}</p>
        {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      </div>
    </Panel>
  )
}

function formatDateTime(iso: string | null) {
  if (!iso) return "Never"
  const d = new Date(iso)
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d)
}