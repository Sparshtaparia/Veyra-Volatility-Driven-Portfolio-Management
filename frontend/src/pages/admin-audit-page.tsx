import { Panel, PanelHeader, Badge } from "@/components/ui/primitives"

const demoAudit = [
  { timestamp: "2026-09-17 09:12:04", user: "sparsh@example.com", action: "portfolio.evaluate", resource: "portfolio:My Portfolio", result: "OK" },
  { timestamp: "2026-09-16 14:03:11", user: "sparsh@example.com", action: "rebalance.execute_paper", resource: "portfolio:My Portfolio", result: "OK" },
  { timestamp: "2026-09-16 14:03:12", user: "sparsh@example.com", action: "feedback.update_threshold", resource: "portfolio:My Portfolio", result: "OK" },
  { timestamp: "2026-09-01 09:00:41", user: "aarav@example.com", action: "auth.sign_in", resource: "session", result: "OK" },
]

export function AdminAuditPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-slate-500">ADMIN</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Audit Logs</h1>
      </header>
      <Panel className="mt-6">
        <PanelHeader title="Audit trail" subtitle="Representative entries — the audit logger forwards every protected action here." />
        <div className="overflow-x-auto px-6 py-4">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="pb-3 pr-4 font-semibold">Timestamp</th><th className="pb-3 pr-4 font-semibold">User</th><th className="pb-3 pr-4 font-semibold">Action</th><th className="pb-3 pr-4 font-semibold">Resource</th><th className="pb-3 font-semibold">Result</th></tr>
            </thead>
            <tbody>
              {demoAudit.map((item, index) => (
                <tr key={index} className="border-b border-slate-100 last:border-0">
                  <td className="py-3.5 pr-4 font-mono text-xs tabular-nums">{item.timestamp}</td>
                  <td className="py-3.5 pr-4 text-slate-700">{item.user}</td>
                  <td className="py-3.5 pr-4 font-medium text-slate-900">{item.action}</td>
                  <td className="py-3.5 pr-4 text-slate-500">{item.resource}</td>
                  <td className="py-3.5"><Badge tone="emerald">{item.result}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}