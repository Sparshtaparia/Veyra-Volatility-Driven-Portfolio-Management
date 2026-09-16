import type { Holding } from "@/api/portfolios"
import { currency, percent } from "@/lib/format"

export function HoldingsTable({ holdings }: { holdings: Holding[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="pb-3 pr-4 font-semibold">Asset</th>
            <th className="pb-3 pr-4 text-right font-semibold">Qty</th>
            <th className="pb-3 pr-4 text-right font-semibold">Price</th>
            <th className="pb-3 pr-4 text-right font-semibold">Value</th>
            <th className="pb-3 text-right font-semibold">Weight</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr key={holding.id} className="border-b border-slate-100 last:border-0">
              <td className="py-3.5 pr-4">
                <span className="font-semibold text-slate-950">{holding.ticker}</span>
              </td>
              <td className="py-3.5 pr-4 text-right tabular-nums text-slate-600">{holding.quantity.toLocaleString("en-IN")}</td>
              <td className="py-3.5 pr-4 text-right tabular-nums text-slate-600">{currency(holding.current_price, "INR")}</td>
              <td className="py-3.5 pr-4 text-right tabular-nums font-medium text-slate-900">{currency(holding.market_value, "INR")}</td>
              <td className="py-3.5 text-right font-semibold text-slate-950">{percent(holding.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}