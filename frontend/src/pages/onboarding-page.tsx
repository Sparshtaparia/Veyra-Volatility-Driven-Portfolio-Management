import { useState } from "react"
import { ArrowLeft, ArrowRight, Check, Plus, Trash2 } from "lucide-react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/auth-context"
import { useAddHolding, useCreatePortfolio } from "@/hooks/use-portfolio"
import { Field, Notice, Panel, SelectInput, TextInput } from "@/components/ui/primitives"

const steps = ["Profile", "Portfolio", "Holdings", "Finish"]

type HoldingRow = { ticker: string; quantity: string; price: string }

const suggested = [
  { ticker: "TCS", quantity: "20", price: "3500" },
  { ticker: "INFY", quantity: "15", price: "1600" },
  { ticker: "HDFC", quantity: "10", price: "1800" },
]

export function OnboardingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const createPortfolio = useCreatePortfolio()
  const portfolioId = createPortfolio.data?.portfolio_id ?? null
  const addHolding = useAddHolding(portfolioId)
  const [step, setStep] = useState(0)
  const [name, setName] = useState("My Portfolio")
  const [currency, setCurrency] = useState("INR")
  const [frequency, setFrequency] = useState("Monthly")
  const [rows, setRows] = useState<HoldingRow[]>([])
  const [error, setError] = useState<string | undefined>()
  const [submitting, setSubmitting] = useState(false)

  if (!user) return <Navigate to="/sign-up" replace />

  async function createAndContinue() {
    setError(undefined)
    createPortfolio.mutate(
      { name: name.trim() || "My Portfolio", currency },
      { onSuccess: () => setStep(2), onError: (err) => setError(err.message) }
    )
  }

  async function finishHoldings() {
    setError(undefined)
    if (!portfolioId || rows.length === 0) {
      setError("Add at least one holding before continuing.")
      return
    }
    setSubmitting(true)
    try {
      for (const row of rows) {
        await addHolding.mutateAsync({ ticker: row.ticker.toUpperCase(), quantity: Number(row.quantity), average_price: Number(row.price), current_price: Number(row.price) })
      }
      setStep(3)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save holdings.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-5 py-10">
      <div className="w-full max-w-xl">
        <div className="mb-8 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="grid size-9 place-items-center rounded-lg bg-emerald-500 text-sm font-bold text-white">V</span>
            <span className="text-xl font-semibold tracking-tight">Veyra</span>
          </Link>
          <p className="text-sm text-slate-500">Step {step + 1} of 4</p>
        </div>

        <ol className="mb-8 flex items-center gap-2">
          {steps.map((label, index) => (
            <li key={label} className="flex flex-1 items-center gap-2">
              <span className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${index <= step ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                {index < step ? <Check className="size-3.5" /> : index + 1}
              </span>
              <span className={`hidden text-xs font-medium sm:block ${index <= step ? "text-slate-900" : "text-slate-400"}`}>{label}</span>
              {index < steps.length - 1 && <span className="h-px flex-1 bg-slate-200" />}
            </li>
          ))}
        </ol>

        <Panel className="p-7">
          {step === 0 && (
            <>
              <p className="text-sm font-semibold text-emerald-700">VEYRA ONBOARDING</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">Welcome to Veyra, {user.name.split(" ")[0]}</h1>
              <p className="mt-3 leading-6 text-slate-600">Let's set up your portfolio. Veyra starts from the portfolio you actually hold, then tells you when it needs to change.</p>
              <button onClick={() => setStep(1)} className="mt-7 inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Get started <ArrowRight className="size-4" /></button>
            </>
          )}

          {step === 1 && (
            <>
              <p className="text-sm font-semibold text-emerald-700">STEP 2 · PORTFOLIO</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">Set up your portfolio</h1>
              <p className="mt-3 text-sm text-slate-600">Tell Veyra what you're monitoring. You can change these later in Settings.</p>
              <div className="mt-6 space-y-4">
                <Field label="Portfolio Name"><TextInput value={name} onChange={(e) => setName(e.target.value)} /></Field>
                <Field label="Base Currency">
                  <SelectInput value={currency} onChange={(e) => setCurrency(e.target.value)}>
                    <option value="INR">INR — Indian Rupee</option>
                    <option value="USD">USD — US Dollar</option>
                  </SelectInput>
                </Field>
                <Field label="Evaluation Frequency">
                  <SelectInput value={frequency} onChange={(e) => setFrequency(e.target.value)}>
                    <option>Monthly</option>
                    <option>Weekly</option>
                    <option>Quarterly</option>
                  </SelectInput>
                </Field>
              </div>
              {error && <Notice text={error} />}
              <div className="mt-7 flex items-center justify-between">
                <button onClick={() => setStep(0)} className="inline-flex h-11 items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950"><ArrowLeft className="size-4" /> Back</button>
                <button onClick={createAndContinue} disabled={createPortfolio.isPending} className="inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white disabled:opacity-60">
                  {createPortfolio.isPending ? "Creating…" : "Continue"} <ArrowRight className="size-4" />
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <p className="text-sm font-semibold text-emerald-700">STEP 3 · HOLDINGS</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">Add holdings</h1>
              <p className="mt-3 text-sm text-slate-600">Enter the securities you currently hold. Veyra needs quantity and average price to estimate your position.</p>

              <HoldingRowInput onAdd={(row) => setRows((prev) => [...prev, row])} />

              {rows.length > 0 && (
                <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr><th className="px-4 py-2.5 font-semibold">Ticker</th><th className="px-4 py-2.5 text-right font-semibold">Quantity</th><th className="px-4 py-2.5 text-right font-semibold">Avg Price</th><th className="w-10" /></tr>
                    </thead>
                    <tbody>
                      {rows.map((row, index) => (
                        <tr key={index} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-3 font-semibold">{row.ticker.toUpperCase()}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{Number(row.quantity).toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right tabular-nums">₹{Number(row.price).toLocaleString("en-IN")}</td>
                          <td className="px-2 py-3"><button onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))} className="grid size-7 place-items-center rounded text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Remove"><Trash2 className="size-4" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <button onClick={() => setRows(suggested)} className="mt-4 text-sm font-semibold text-emerald-700 hover:underline">Use sample holdings (TCS / INFY / HDFC)</button>

              {error && <Notice text={error} />}
              <div className="mt-7 flex items-center justify-between">
                <button onClick={() => setStep(1)} className="inline-flex h-11 items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950"><ArrowLeft className="size-4" /> Back</button>
                <button onClick={finishHoldings} disabled={submitting || rows.length === 0} className="inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white disabled:opacity-60">
                  {submitting ? "Saving…" : "Continue"} <ArrowRight className="size-4" />
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="py-6 text-center">
              <span className="mx-auto grid size-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><Check className="size-8" /></span>
              <h1 className="mt-5 text-2xl font-semibold tracking-tight">Your portfolio is ready</h1>
              <p className="mx-auto mt-3 max-w-sm leading-6 text-slate-600">Veyra will evaluate <strong>{name}</strong> ({rows.length} holdings, base currency {currency}, {frequency.toLowerCase()} frequency) and tell you when it needs to change.</p>
              <button onClick={() => navigate("/app")} className="mt-7 inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-6 text-sm font-semibold text-white">Go to Dashboard <ArrowRight className="size-4" /></button>
            </div>
          )}
        </Panel>
      </div>
    </main>
  )
}

function HoldingRowInput({ onAdd }: { onAdd: (row: HoldingRow) => void }) {
  const [ticker, setTicker] = useState("")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  return (
    <form
      className="mt-5 grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]"
      onSubmit={(event) => {
        event.preventDefault()
        if (!ticker.trim() || !quantity || !price) return
        onAdd({ ticker: ticker.trim(), quantity, price })
        setTicker("")
        setQuantity("")
        setPrice("")
      }}
    >
      <TextInput value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="Ticker (e.g. TCS)" required />
      <TextInput value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Quantity" type="number" min="0" step="any" required />
      <TextInput value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Avg price (₹)" type="number" min="0" step="any" required />
      <button className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-4 text-sm font-semibold text-emerald-800 hover:bg-emerald-100"><Plus className="size-4" /> Add</button>
    </form>
  )
}