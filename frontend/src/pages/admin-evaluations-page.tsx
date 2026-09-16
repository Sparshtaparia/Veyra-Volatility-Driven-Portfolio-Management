import { Panel, PanelHeader, Badge } from "@/components/ui/primitives"

const demoEvaluations = [
  { id: "ev-9f21", portfolio: "My Portfolio", regime: "HIGH VOLATILITY", decision: "REBALANCE_REQUIRED", timestamp: "2026-09-17 09:12", status: "COMPLETED" },
  { id: "ev-8a33", portfolio: "Retirement Fund", regime: "NORMAL", decision: "HOLD", timestamp: "2026-09-15 18:04", status: "COMPLETED" },
  { id: "ev-7c15", portfolio: "My Portfolio", regime: "NORMAL", decision: "HOLD", timestamp: "2026-09-01 09:00", status: "COMPLETED" },
]

export function AdminEvaluationsPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-slate-500">ADMIN</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Evaluations</h1>
      </header>
      <Panel className="mt-6">
        <PanelHeader title="Evaluation runs" subtitle="Representative rows — a dedicated evaluations service will list every run across tenants." />
        <div className="overflow-x-auto px-6 py-4">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="pb-3 pr-4 font-semibold">Evaluation ID</th><th className="pb-3 pr-4 font-semibold">Portfolio</th><th className="pb-3 pr-4 font-semibold">Regime</th><th className="pb-3 pr-4 font-semibold">Decision</th><th className="pb-3 pr-4 font-semibold">Timestamp</th><th className="pb-3 font-semibold">Status</th></tr>
            </thead>
            <tbody>
              {demoEvaluations.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-3.5 pr-4 font-mono text-xs">{item.id}</td>
                  <td className="py-3.5 pr-4 font-medium">{item.portfolio}</td>
                  <td className="py-3.5 pr-4">{item.regime}</td>
                  <td className="py-3.5 pr-4"><Badge tone={item.decision === "REBALANCE_REQUIRED" ? "amber" : "emerald"}>{item.decision}</Badge></td>
                  <td className="py-3.5 pr-4 tabular-nums text-slate-500">{item.timestamp}</td>
                  <td className="py-3.5"><Badge tone="emerald">{item.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}