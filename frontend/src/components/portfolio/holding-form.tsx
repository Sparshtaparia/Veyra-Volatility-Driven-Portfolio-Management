import { useState } from "react"
import { Plus } from "lucide-react"
import { useAddHolding } from "@/hooks/use-portfolio"
import { Field, Notice, TextInput } from "@/components/ui/primitives"

import { useToast } from "@/components/common/toast"

const INDIAN_STOCKS = [
  "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
  "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", 
  "BAJFINANCE", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", 
  "ULTRACEMCO", "WIPRO", "NESTLEIND", "POWERGRID", "NTPC", "M&M", 
  "TATASTEEL", "TECHM", "HCLTECH", "ONGC", "HINDALCO", "BAJAJFINSV", 
  "JSWSTEEL", "ADANIPORTS", "GRASIM", "TATAMOTORS", "DIVISLAB", 
  "INDUSINDBK", "CIPLA", "APOLLOHOSP", "BRITANNIA", "BAJAJ-AUTO", 
  "EICHERMOT", "COALINDIA", "UPL", "TATACONSUM", "HEROMOTOCO", 
  "DRREDDY", "SHREECEM", "BPCL", "LTIM", "ADANIENT"
]

export function AddHoldingForm({ portfolioId, onAdded }: { portfolioId: string; onAdded?: () => void }) {
  const [ticker, setTicker] = useState("")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const addHolding = useAddHolding(portfolioId)
  const { toast } = useToast()

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        addHolding.mutate(
          { ticker: ticker.toUpperCase(), quantity: Number(quantity), average_price: Number(price), current_price: Number(price) },
          {
            onSuccess: () => {
              toast({ title: `Added ${ticker.toUpperCase()}`, type: "success" })
              setTicker("")
              setQuantity("")
              setPrice("")
              onAdded?.()
            },
            onError: (err) => {
              toast({ title: "Failed to add holding", description: err.message, type: "error" })
            }
          }
        )
      }}
      className="rounded-xl border border-slate-200 bg-white p-6"
    >
      <h2 className="flex items-center gap-2 text-base font-semibold text-slate-950"><Plus className="size-4 text-emerald-600" /> Add a holding</h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <Field label="Ticker">
          <TextInput value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TCS" list="ticker-suggestions" autoFocus required />
          <datalist id="ticker-suggestions">
            {INDIAN_STOCKS.map(symbol => (
              <option key={symbol} value={symbol} />
            ))}
          </datalist>
        </Field>
        <Field label="Quantity"><TextInput value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="20" type="number" min="0" step="any" required /></Field>
        <Field label="Average price"><TextInput value={price} onChange={(e) => setPrice(e.target.value)} placeholder="₹3,500" type="number" min="0" step="any" required /></Field>
      </div>
      {addHolding.error && <Notice text={addHolding.error.message} />}
      <button disabled={addHolding.isPending} className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white disabled:opacity-60">
        <Plus className="size-4" /> {addHolding.isPending ? "Saving…" : "Save holding"}
      </button>
    </form>
  )
}