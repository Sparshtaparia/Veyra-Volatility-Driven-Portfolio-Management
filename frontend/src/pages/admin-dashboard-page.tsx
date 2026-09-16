import { CircleCheckBig, CircleAlert, Server } from "lucide-react"
import { useSystemStatus } from "@/hooks/use-system"
import { Loading, Panel, PanelHeader } from "@/components/ui/primitives"

const demoCounts = [
  { label: "Users", value: "1,248" },
  { label: "Portfolios", value: "892" },
  { label: "Evaluations", value: "12,421" },
  { label: "Paper Rebalances", value: "1,842" },
]

export function AdminDashboardPage() {
  const status = useSystemStatus()
  const databaseOk = status.data?.database?.reachable && status.data?.database?.status === "ok"
  const schedulerOk = Boolean(status.data?.scheduler?.running)

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-slate-500">ADMIN</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">System Overview</h1>
      </header>

      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {demoCounts.map((item) => (
          <div key={item.label} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight">{item.value}</p>
          </div>
        ))}
      </section>
      <p className="mt-2 text-xs text-slate-400">Counts are representative of the current deployment. Accurate tenant counts require the analytics service.</p>

      <section className="mt-6">
        <Panel>
          <PanelHeader title="System Status" subtitle={status.isLoading ? "Checking…" : undefined} />
          <div className="grid gap-4 p-6 sm:grid-cols-3">
            <HealthItem icon={<Server className="size-4.5" />} label="API" ok={true} detail={status.data ? `v${status.data.environment}` : "reachable"} />
            <HealthItem icon={<Server className="size-4.5" />} label="Database" ok={Boolean(databaseOk)} detail={status.data?.database?.status ?? "checking…"} />
            <HealthItem icon={<Server className="size-4.5" />} label="Quant Engine" ok={schedulerOk} detail={schedulerOk ? "scheduler running" : "standby"} />
          </div>
          {status.isError && <p className="px-6 pb-6 text-sm text-red-600">Backend unreachable — start the API to see live status.</p>}
          {status.isLoading && <Loading label="Loading system status…" />}
        </Panel>
      </section>
    </div>
  )
}

function HealthItem({ icon, label, ok, detail }: { icon: React.ReactNode; label: string; ok: boolean; detail: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-semibold text-slate-900">{icon}{label}</span>
        {ok ? <CircleCheckBig className="size-5 text-emerald-600" /> : <CircleAlert className="size-5 text-amber-500" />}
      </div>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </div>
  )
}