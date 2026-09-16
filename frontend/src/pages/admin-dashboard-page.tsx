import { CircleCheckBig, CircleAlert, Server, Users, Activity, BarChart4, LayoutDashboard, Globe, Database, Cpu } from "lucide-react"
import { useSystemStatus } from "@/hooks/use-system"
import { Loading } from "@/components/ui/primitives"

const demoCounts = [
  { label: "Active Users", value: "1,248", icon: <Users className="size-5" />, trend: "+12%" },
  { label: "Portfolios", value: "892", icon: <LayoutDashboard className="size-5" />, trend: "+8%" },
  { label: "Daily Evaluations", value: "12,421", icon: <Activity className="size-5" />, trend: "+24%" },
  { label: "Paper Rebalances", value: "1,842", icon: <BarChart4 className="size-5" />, trend: "+5%" },
]

export function AdminDashboardPage() {
  const status = useSystemStatus()
  const databaseOk = status.data?.database?.reachable && status.data?.database?.status === "ok"
  const schedulerOk = Boolean(status.data?.scheduler?.running)

  return (
    <div className="mx-auto max-w-6xl animate-fade-up">
      <header className="mb-8">
        <div className="flex items-center gap-2">
          <Globe className="size-5 text-emerald-600" />
          <p className="text-sm font-bold tracking-wider text-slate-500 uppercase">Admin Command Center</p>
        </div>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">System Overview</h1>
        <p className="mt-2 text-sm text-slate-500">Monitor Veyra's core infrastructure and user activity metrics.</p>
      </header>

      {/* Stats Grid */}
      <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {demoCounts.map((item, i) => (
          <div 
            key={item.label} 
            className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1 animate-fade-up"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <div className="absolute -right-6 -top-6 size-24 rounded-full bg-slate-50 opacity-50 transition-transform group-hover:scale-150" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-xl bg-slate-950 text-white">
                  {item.icon}
                </span>
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  {item.trend}
                </span>
              </div>
              <p className="mt-4 text-3xl font-black tabular-nums text-slate-900">{item.value}</p>
              <p className="mt-1 text-sm font-medium text-slate-500">{item.label}</p>
            </div>
          </div>
        ))}
      </section>
      
      <p className="mt-4 flex items-center gap-2 text-xs text-slate-400">
        <CircleAlert className="size-3.5" /> Counts are representative of the current deployment context.
      </p>

      {/* System Status Panel */}
      <section className="mt-10 animate-fade-up" style={{ animationDelay: "400ms" }}>
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">System Status</h2>
                <p className="text-sm text-slate-500">Live health checks for core services</p>
              </div>
              {status.isLoading && <Loading label="" />}
            </div>
          </div>
          
          <div className="grid gap-6 p-6 sm:grid-cols-3">
            <HealthItem 
              icon={<Server className="size-5" />} 
              label="API Gateway" 
              ok={true} 
              detail={status.data ? `v${status.data.environment}` : "reachable"} 
              delay={500}
            />
            <HealthItem 
              icon={<Database className="size-5" />} 
              label="Primary Database" 
              ok={Boolean(databaseOk)} 
              detail={status.data?.database?.status ?? "checking…"} 
              delay={600}
            />
            <HealthItem 
              icon={<Cpu className="size-5" />} 
              label="Quant Engine" 
              ok={schedulerOk} 
              detail={schedulerOk ? "scheduler running" : "standby"} 
              delay={700}
            />
          </div>
          
          {status.isError && (
            <div className="mx-6 mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 flex items-center gap-3">
              <CircleAlert className="size-5 text-rose-600" />
              <p className="text-sm font-medium text-rose-800">Backend is currently unreachable. Start the API service to view live status.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

function HealthItem({ icon, label, ok, detail, delay }: { icon: React.ReactNode; label: string; ok: boolean; detail: string; delay: number }) {
  return (
    <div 
      className={`relative overflow-hidden rounded-xl border p-5 transition-all animate-fade-up ${ok ? "border-emerald-200 bg-emerald-50/30" : "border-amber-200 bg-amber-50"}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`grid size-10 place-items-center rounded-lg ${ok ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
            {icon}
          </span>
          <div>
            <p className="font-bold text-slate-900">{label}</p>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{detail}</p>
          </div>
        </div>
        {ok ? (
          <CircleCheckBig className="size-6 text-emerald-500 drop-shadow-sm" />
        ) : (
          <CircleAlert className="size-6 text-amber-500 drop-shadow-sm" />
        )}
      </div>
    </div>
  )
}