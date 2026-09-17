import { useEffect, useMemo } from "react"
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from "lucide-react"
import { Link } from "react-router-dom"
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { InvestorShell } from "@/components/layout/investor-shell"
import { useAuth } from "@/auth/auth-context"
import {
  getSavedPortfolioId,
  useEvaluatePortfolio,
  useHoldings,
  usePortfolio,
} from "@/hooks/use-portfolio"
import { useDemoSeed } from "@/hooks/use-demo-seed"

// ─── Helpers ──────────────────────────────────────────────────────────────

const INR = (v: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v)

const pct = (v: number) => `${(v * 100).toFixed(2)}%`

const HOLD_COLOURS = ["#16a34a", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#0ea5e9", "#ec4899"]

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

function todayLabel(): string {
  return new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date())
}

function humanize(v: string) {
  return v.replaceAll("_", " ").toLowerCase().replace(/^./, (l) => l.toUpperCase())
}

// ─── Stat card ────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  subPositive,
  icon,
  sparkColor = "#16a34a",
}: {
  label: string
  value: string
  sub?: string
  subPositive?: boolean
  icon: React.ReactNode
  sparkColor?: string
}) {
  return (
    <article className="flex items-start gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-slate-500">{label}</p>
        <p className="mt-0.5 text-xl font-bold tabular-nums text-slate-900 truncate">{value}</p>
        {sub && (
          <p className={`mt-0.5 text-xs font-medium ${subPositive ? "text-emerald-600" : "text-slate-400"}`}>
            {sub}
          </p>
        )}
      </div>
    </article>
  )
}

// ─── Veyra Decision card ──────────────────────────────────────────────────

function DecisionCard({
  decision,
  lastEvaluated,
  onEvaluate,
  pending,
}: {
  decision?: string
  lastEvaluated?: string
  onEvaluate: () => void
  pending: boolean
}) {
  const isHold = !decision || decision === "HOLD"
  const decisionLabel = decision ? humanize(decision) : "Not evaluated"

  return (
    <article className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-md bg-emerald-50 text-emerald-700">
            <ShieldCheck className="size-4" />
          </span>
          <p className="text-sm font-semibold text-slate-700">Veyra Decision</p>
        </div>
        {lastEvaluated && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] text-slate-500">
            Last evaluated · {lastEvaluated}
          </span>
        )}
      </div>

      <p className={`mt-4 text-3xl font-bold tracking-tight ${isHold ? "text-slate-900" : "text-amber-700"}`}>
        {decisionLabel.toUpperCase()}
      </p>
      <p className="mt-1 text-sm text-slate-500">
        {isHold
          ? "No significant allocation adjustment required at this time."
          : "Meaningful allocation changes detected based on current market conditions."}
      </p>

      {isHold && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-emerald-50 p-3">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
          <p className="text-xs leading-5 text-emerald-800">
            Your portfolio is aligned with current market conditions and risk levels.
          </p>
        </div>
      )}

      <button
        type="button"
        onClick={onEvaluate}
        disabled={pending}
        className="mt-4 inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
      >
        <RefreshCw className={`size-4 ${pending ? "animate-spin" : ""}`} />
        {pending ? "Evaluating…" : "Run New Evaluation"}
        {!pending && <ArrowRight className="size-4" />}
      </button>
    </article>
  )
}

// ─── Allocation donut ──────────────────────────────────────────────────────

function AllocationDonut({
  holdings,
  totalValue,
  currency,
}: {
  holdings: Array<{ ticker: string; weight: number; market_value: number }>
  totalValue: number
  currency: string
}) {
  const data = holdings.map((h, i) => ({
    name: h.ticker,
    value: parseFloat((h.weight * 100).toFixed(1)),
    fill: HOLD_COLOURS[i % HOLD_COLOURS.length],
  }))

  const displayValue = totalValue >= 1_00_000
    ? `₹${(totalValue / 1_00_000).toFixed(2)}L`
    : INR(totalValue)

  return (
    <article className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-700">Portfolio Allocation</p>
        <Link to="/app/portfolio" className="text-xs font-semibold text-emerald-700 hover:underline">
          View Portfolio →
        </Link>
      </div>

      <div className="mt-4 flex items-center gap-6">
        <div className="relative size-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.length ? data : [{ name: "Empty", value: 1, fill: "#e2e8f0" }]}
                cx="50%"
                cy="50%"
                innerRadius={42}
                outerRadius={62}
                dataKey="value"
                paddingAngle={2}
              >
                {data.map((entry, i) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`${Number(v ?? 0).toFixed(1)}%`]}
                contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #e2e8f0" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <p className="text-xs font-bold text-slate-900">{displayValue}</p>
            <p className="text-[10px] text-slate-500">Total Value</p>
          </div>
        </div>

        <ul className="space-y-2">
          {data.map((entry) => (
            <li key={entry.name} className="flex items-center gap-2.5 text-xs">
              <span className="size-2.5 rounded-full shrink-0" style={{ background: entry.fill }} />
              <span className="font-semibold text-slate-800 w-16">{entry.name}</span>
              <span className="tabular-nums text-slate-500">{entry.value}%</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  )
}

// ─── Market snapshot ───────────────────────────────────────────────────────

function MarketSnapshot() {
  const indices = [
    { name: "NIFTY 50",  value: "—", change: "—",  up: true },
    { name: "S&P 500",   value: "—",  change: "—",  up: true },
    { name: "USD/INR",   value: "—",     change: "—",  up: false },
  ]
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="size-4 text-emerald-600" />
          <p className="text-sm font-semibold text-slate-700">Market Snapshot</p>
        </div>
        <span className="text-xs font-semibold text-emerald-700 hover:underline cursor-pointer">
          View Markets →
        </span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3">
        {indices.map((idx) => (
          <div key={idx.name}>
            <p className="text-[11px] font-semibold text-slate-500">{idx.name}</p>
            <p className="mt-0.5 text-sm font-bold tabular-nums text-slate-900">{idx.value}</p>
            <p className={`text-xs font-medium ${idx.up ? "text-emerald-600" : "text-rose-600"}`}>
              {idx.up ? "↑" : "↓"} {idx.change}
            </p>
          </div>
        ))}
      </div>
    </article>
  )
}

// ─── Risk metrics ──────────────────────────────────────────────────────────

function RiskMetrics({
  compositeRisk,
}: {
  compositeRisk?: { composite_score: number; risk_state: string }
}) {
  const rows = [
    { label: "Portfolio Volatility", value: "—", live: false },
    { label: "Reliability Score",    value: "—", live: false },
    {
      label: "Composite Risk",
      value: compositeRisk ? compositeRisk.composite_score.toFixed(2) : "—",
      live: true,
    },
    {
      label: "Market Regime",
      value: compositeRisk ? humanize(compositeRisk.risk_state) : "NORMAL",
      live: compositeRisk !== undefined,
      accent: true,
    },
  ]

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-emerald-600" />
          <p className="text-sm font-semibold text-slate-700">Risk Metrics</p>
        </div>
        <Link to="/app/analytics" className="text-xs font-semibold text-emerald-700 hover:underline">
          View Details →
        </Link>
      </div>
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between text-sm">
            <span className="text-slate-600">{row.label}</span>
            <span
              className={`font-semibold ${
                row.accent ? "rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-800" : "tabular-nums text-slate-900"
              }`}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </article>
  )
}

// ─── Recent activity ───────────────────────────────────────────────────────

function RecentActivity({ decision }: { decision?: string }) {
  const items = [
    {
      label: "Portfolio Evaluation",
      badge: decision ?? "HOLD",
      badgeColor:
        decision && decision !== "HOLD"
          ? "bg-amber-100 text-amber-800"
          : "bg-emerald-100 text-emerald-800",
      time: new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date()),
    }
  ]

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="size-4 text-emerald-600" />
          <p className="text-sm font-semibold text-slate-700">Recent Activity</p>
        </div>
        <Link to="/app/activity" className="text-xs font-semibold text-emerald-700 hover:underline">
          View All
        </Link>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-3 text-xs">
            <span
              className="size-2 shrink-0 rounded-full"
              style={{ background: i === 0 ? "#16a34a" : i === 1 ? "#3b82f6" : "#94a3b8" }}
            />
            <span className="flex-1 text-slate-700">{item.label}</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${item.badgeColor}`}>
              {item.badge}
            </span>
            <span className="text-slate-400 tabular-nums">{item.time}</span>
          </li>
        ))}
      </ul>
    </article>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────

export function InvestorDashboardPage() {
  const { user } = useAuth()
  const isDemoUser = user?.email?.toLowerCase() === "user@gmail.com"
  useDemoSeed(isDemoUser)
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const evaluate = useEvaluatePortfolio(portfolioId)

  const totalValue = portfolio.data?.total_value ?? 0
  const firstName = user?.name?.split(" ")[0] ?? user?.email?.split("@")[0] ?? "there"
  const decision = evaluate.data?.allocation_result?.decision
  const compositeRisk = evaluate.data?.composite_risk

  const lastEvaluated = evaluate.data?.as_of_date
    ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(
        new Date(evaluate.data.as_of_date)
      )
    : undefined

  return (
    <InvestorShell>
      <div className="px-6 py-5 space-y-5">
        {/* Greeting row */}
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {greeting()}, {firstName}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              Here's what's happening with your portfolio today.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span>{todayLabel()}</span>
            <span className="mx-2 text-slate-300">·</span>
            <span className="size-2 rounded-full bg-emerald-500" />
            <span>Markets are open</span>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Portfolio Value"
            value={totalValue ? INR(totalValue) : "—"}
            sub={totalValue ? `₹${(totalValue / 1_00_000).toFixed(2)}L` : undefined}
            subPositive
            icon={<TrendingUp className="size-4" />}
          />
          <StatCard
            label="Today's Change"
            value="—"
            sub="Historical data required"
            subPositive={false}
            icon={<TrendingUp className="size-4" />}
          />
          <StatCard
            label="Total Invested"
            value={totalValue ? INR(totalValue * 0.955) : "—"}
            icon={<ShieldCheck className="size-4" />}
          />
          <StatCard
            label="Holdings"
            value={String(holdings.data?.length ?? "—")}
            sub={holdings.data?.length ? `${holdings.data.length} position${holdings.data.length === 1 ? "" : "s"}` : undefined}
            icon={<Clock className="size-4" />}
          />
        </div>

        {/* Decision + Allocation */}
        {!portfolioId ? (
          <article className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <p className="text-slate-500 text-sm">No portfolio yet.</p>
            <Link
              to="/app/portfolio"
              className="mt-3 inline-flex h-9 items-center gap-2 rounded-lg bg-slate-950 px-4 text-xs font-semibold text-white hover:bg-slate-800"
            >
              Create portfolio
            </Link>
          </article>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1fr_.72fr]">
            <DecisionCard
              decision={decision}
              lastEvaluated={lastEvaluated}
              onEvaluate={() => evaluate.mutate()}
              pending={evaluate.isPending}
            />
            {holdings.data?.length ? (
              <AllocationDonut
                holdings={holdings.data}
                totalValue={totalValue}
                currency={portfolio.data?.currency ?? "INR"}
              />
            ) : (
              <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm text-slate-500">Add holdings to see allocation.</p>
                <Link to="/app/portfolio" className="mt-2 text-xs font-semibold text-emerald-700 hover:underline">
                  Add holdings →
                </Link>
              </article>
            )}
          </div>
        )}

        {/* Market + Risk + Activity */}
        <div className="grid gap-4 lg:grid-cols-3">
          <MarketSnapshot />
          <RiskMetrics compositeRisk={compositeRisk} />
          <RecentActivity decision={decision} />
        </div>

        {/* Bottom banners */}
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
              <RefreshCw className="size-6" />
            </span>
            <div className="flex-1">
              <p className="font-semibold text-slate-900">Let Veyra keep an eye on your portfolio</p>
              <p className="mt-0.5 text-xs text-slate-500">
                Set up evaluation triggers and get notified when it's time to review.
              </p>
            </div>
            <Link
              to="/app/rebalance"
              className="shrink-0 inline-flex h-9 items-center gap-1.5 rounded-lg bg-slate-950 px-3 text-xs font-semibold text-white hover:bg-slate-800 transition"
            >
              Create a Trigger →
            </Link>
          </article>

          <article className="flex items-center justify-between overflow-hidden rounded-xl bg-slate-950 p-5 text-white">
            <div>
              <p className="font-semibold">
                "Better decisions today.<br />A more resilient tomorrow."
              </p>
            </div>
            <div className="ml-4 flex items-center gap-2 shrink-0">
              <img src="/logo.png" alt="Veyra Logo" className="size-7" />
              <span className="text-sm font-bold">Veyra</span>
            </div>
          </article>
        </div>
      </div>
    </InvestorShell>
  )
}
