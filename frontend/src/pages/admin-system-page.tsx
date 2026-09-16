import { CircleCheckBig, CircleAlert, Server } from "lucide-react"
import { useSystemStatus } from "@/hooks/use-system"
import { Loading, Panel, PanelHeader } from "@/components/ui/primitives"

export function AdminSystemPage() {
  const status = useSystemStatus()

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-slate-500">ADMIN</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">System</h1>
      </header>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Services" subtitle="Live checks against the backend" />
          <div className="space-y-3 p-6">
            <ServiceRow label="API" ok={!status.isError} detail="REST API + auth gateway" />
            <ServiceRow label="Database" ok={Boolean(status.data?.database?.reachable)} detail={status.data?.database ? `${status.data.database.status} · ${status.data.database.schema_status}` : "not checked yet"} />
            <ServiceRow label="Market data provider" ok={Boolean(status.data?.market_data?.provider)} detail={status.data?.market_data?.provider ?? "not checked yet"} />
            <ServiceRow label="Background jobs (scheduler)" ok={Boolean(status.data?.scheduler?.running)} detail={status.data?.scheduler?.running ? "scheduler running" : "not running"} />
          </div>
          {status.isError && <p className="px-6 pb-6 text-sm text-red-600">Backend unreachable — start the API to see live status.</p>}
          {status.isLoading && <Loading label="Loading system status…" />}
        </Panel>

        <Panel>
          <PanelHeader title="Scheduled run counts" subtitle="From the operations repository" />
          <div className="p-6">
            {status.data?.scheduled_run_counts && Object.keys(status.data.scheduled_run_counts).length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(status.data.scheduled_run_counts).map(([key, value]) => (
                  <div key={key} className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">{key.replace("_", " ")}</p><p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p></div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No scheduled runs recorded yet. The scheduler processes portfolio evaluations on its configured interval.</p>
            )}
          </div>
        </Panel>
      </div>
    </div>
  )
}

function ServiceRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-lg bg-white text-slate-600 shadow-sm"><Server className="size-4.5" /></span>
        <div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="text-xs text-slate-500">{detail}</p>
        </div>
      </div>
      {ok ? <CircleCheckBig className="size-5 shrink-0 text-emerald-600" /> : <CircleAlert className="size-5 shrink-0 text-amber-500" />}
    </div>
  )
}