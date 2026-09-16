import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import type { Holding } from "@/api/portfolios"
import { percent } from "@/lib/format"

const palette = ["#10b981", "#6366f1", "#f59e0b", "#0ea5e9", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316", "#64748b", "#e11d48"]

export function PortfolioDonut({ holdings, size = 220 }: { holdings: Holding[]; size?: number }) {
  const data = holdings.map((h, index) => ({ name: h.ticker, value: Math.max(h.weight * 100, 1), color: palette[index % palette.length] }))
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={2} strokeWidth={0}>
            {data.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
          </Pie>
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="text-2xl font-semibold text-slate-950">100%</p>
          <p className="text-xs text-slate-500">Portfolio</p>
        </div>
      </div>
    </div>
  )
}

export function AllocationLegend({ holdings }: { holdings: Holding[] }) {
  return (
    <ul className="space-y-2.5">
      {holdings.map((h, index) => (
        <li key={h.id} className="flex items-center gap-3 text-sm">
          <span className="size-2.5 shrink-0 rounded-full" style={{ background: palette[index % palette.length] }} />
          <span className="font-medium text-slate-800">{h.ticker}</span>
          <span className="ml-auto font-semibold text-slate-950">{percent(h.weight)}</span>
        </li>
      ))}
    </ul>
  )
}