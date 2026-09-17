import { useState } from "react"
import { Pencil, Trash2, Check, X } from "lucide-react"
import type { Holding } from "@/api/portfolios"
import { currency, percent } from "@/lib/format"
import { useUpdateHolding, useDeleteHolding } from "@/hooks/use-portfolio"
import { TextInput } from "@/components/ui/primitives"

function HoldingRow({ holding, portfolioId }: { holding: Holding, portfolioId: string }) {
  const [editing, setEditing] = useState(false)
  const [qty, setQty] = useState(holding.quantity.toString())
  const [price, setPrice] = useState(holding.current_price.toString())
  
  const update = useUpdateHolding(portfolioId)
  const remove = useDeleteHolding(portfolioId)

  const handleSave = () => {
    update.mutate(
      { ticker: holding.ticker, input: { ticker: holding.ticker, quantity: Number(qty), average_price: Number(price), current_price: Number(price) } },
      { onSuccess: () => setEditing(false) }
    )
  }

  if (editing) {
    return (
      <tr className="border-b border-slate-100 bg-slate-50 last:border-0">
        <td className="py-2.5 pr-4 pl-2 font-semibold text-slate-950">{holding.ticker}</td>
        <td className="py-2.5 pr-4"><TextInput value={qty} onChange={(e) => setQty(e.target.value)} type="number" min="0" step="any" className="h-8 text-right px-2 py-1" /></td>
        <td className="py-2.5 pr-4"><TextInput value={price} onChange={(e) => setPrice(e.target.value)} type="number" min="0" step="any" className="h-8 text-right px-2 py-1" /></td>
        <td className="py-2.5 pr-4 text-right text-slate-400">—</td>
        <td className="py-2.5 text-right">
          <div className="flex items-center justify-end gap-2">
            <button onClick={handleSave} disabled={update.isPending} className="grid size-7 place-items-center rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200"><Check className="size-4" /></button>
            <button onClick={() => setEditing(false)} className="grid size-7 place-items-center rounded bg-slate-200 text-slate-600 hover:bg-slate-300"><X className="size-4" /></button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr className="group border-b border-slate-100 last:border-0 hover:bg-slate-50/50">
      <td className="py-3.5 pr-4 pl-2">
        <span className="font-semibold text-slate-950">{holding.ticker}</span>
      </td>
      <td className="py-3.5 pr-4 text-right tabular-nums text-slate-600">{holding.quantity.toLocaleString("en-IN")}</td>
      <td className="py-3.5 pr-4 text-right tabular-nums text-slate-600">{currency(holding.current_price, "INR")}</td>
      <td className="py-3.5 pr-4 text-right tabular-nums font-medium text-slate-900">{currency(holding.market_value, "INR")}</td>
      <td className="py-3.5 text-right">
        <div className="flex items-center justify-end gap-4">
          <span className="font-semibold text-slate-950">{percent(holding.weight)}</span>
          <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <button onClick={() => setEditing(true)} className="grid size-7 place-items-center rounded text-slate-400 hover:bg-slate-200 hover:text-slate-700"><Pencil className="size-3.5" /></button>
            <button onClick={() => { if (confirm(`Remove ${holding.ticker}?`)) remove.mutate(holding.ticker) }} className="grid size-7 place-items-center rounded text-slate-400 hover:bg-red-100 hover:text-red-700"><Trash2 className="size-3.5" /></button>
          </div>
        </div>
      </td>
    </tr>
  )
}

export function HoldingsTable({ holdings, portfolioId }: { holdings: Holding[], portfolioId: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="pb-3 pr-4 pl-2 font-semibold">Asset</th>
            <th className="pb-3 pr-4 text-right font-semibold">Qty</th>
            <th className="pb-3 pr-4 text-right font-semibold">Price</th>
            <th className="pb-3 pr-4 text-right font-semibold">Value</th>
            <th className="pb-3 text-right font-semibold pr-2">Weight</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <HoldingRow key={holding.id} holding={holding} portfolioId={portfolioId} />
          ))}
        </tbody>
      </table>
    </div>
  )
}