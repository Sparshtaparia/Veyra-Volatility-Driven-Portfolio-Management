import { useState } from "react"
import { BellRing, Plus, Trash2 } from "lucide-react"
import { Field, Panel, PanelHeader, SelectInput, TextInput, Badge, PrimaryButton } from "@/components/ui/primitives"
import { formatDate } from "@/lib/format"

type PriceTrigger = { id: number; ticker: string; threshold: number; reference: string; action: string }

function nextEvaluation() {
  const date = new Date()
  date.setMonth(date.getMonth() + 1)
  return date.toISOString()
}

export function TriggersPage() {
  const [priceTriggers, setPriceTriggers] = useState<PriceTrigger[]>([])
  const [ticker, setTicker] = useState("")
  const [threshold, setThreshold] = useState("10")
  const [reference, setReference] = useState("Today's Open")
  const [action, setAction] = useState("Evaluate Portfolio")

  function createPriceTrigger() {
    if (!ticker.trim()) return
    setPriceTriggers((prev) => [...prev, { id: Date.now(), ticker: ticker.toUpperCase(), threshold: Number(threshold), reference, action }])
    setTicker("")
  }

  const nextRun = nextEvaluation()

  return (
    <div className="mx-auto max-w-4xl">
      <header>
        <p className="text-sm font-semibold text-emerald-700">TRIGGERS</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Evaluation Triggers</h1>
        <p className="mt-1 text-sm text-slate-500">Veyra re-evaluates your portfolio when conditions change — automatically or on a schedule.</p>
      </header>

      <section className="mt-6">
        <Panel>
          <PanelHeader title="Monthly Evaluation" subtitle={`Next: ${formatDate(nextRun)}`} action={<Badge tone="emerald">ON</Badge>} />
          <p className="px-6 py-5 text-sm leading-6 text-slate-600">
            Your portfolio is evaluated automatically each month. When the decision changes, Veyra will surface it on your dashboard.
          </p>
        </Panel>
      </section>

      <section className="mt-6 grid gap-6 md:grid-cols-[1.1fr_.9fr]">
        <Panel>
          <PanelHeader title="Price triggers" subtitle="Notify or evaluate when a holding moves by a set amount." />
          <div className="p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Ticker"><TextInput value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="TCS" /></Field>
              <Field label="Trigger when price changes"><TextInput value={threshold} onChange={(e) => setThreshold(e.target.value)} type="number" min="0" step="any" placeholder="±10" /></Field>
              <Field label="Reference"><SelectInput value={reference} onChange={(e) => setReference(e.target.value)}><option>Today's Open</option><option>Last Close</option><option>Average Price</option></SelectInput></Field>
              <Field label="Action"><SelectInput value={action} onChange={(e) => setAction(e.target.value)}><option>Evaluate Portfolio</option><option>Notify me</option></SelectInput></Field>
            </div>
            <p className="mt-2 text-xs text-slate-500">Trigger at ±{threshold}% vs {reference.toLowerCase()}.</p>
            <PrimaryButton onClick={createPriceTrigger} className="mt-4"><Plus className="size-4" /> Create Trigger</PrimaryButton>
          </div>

          {priceTriggers.length > 0 && (
            <div className="divide-y divide-slate-100 border-t border-slate-100">
              {priceTriggers.map((trigger) => (
                <div key={trigger.id} className="flex items-center justify-between gap-4 px-6 py-4">
                  <div>
                    <p className="font-semibold">{trigger.ticker}</p>
                    <p className="text-sm text-slate-500">{trigger.reference} ±{trigger.threshold}% → {trigger.action}</p>
                  </div>
                  <button onClick={() => setPriceTriggers((prev) => prev.filter((t) => t.id !== trigger.id))} className="grid size-8 place-items-center rounded text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Remove trigger"><Trash2 className="size-4" /></button>
                </div>
              ))}
            </div>
          )}
          {priceTriggers.length === 0 && <p className="border-t border-slate-100 px-6 py-5 text-sm text-slate-500">No price triggers yet.</p>}
        </Panel>

        <Panel>
          <PanelHeader title="Automatic triggers" />
          <div className="space-y-3 p-6">
            <div className="flex items-start gap-3 rounded-lg bg-slate-50 p-4">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-emerald-100 text-emerald-800"><BellRing className="size-4" /></span>
              <div>
                <p className="text-sm font-semibold">Portfolio change</p>
                <p className="mt-0.5 text-sm leading-5 text-slate-600">When a new asset is added → Evaluate portfolio.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-lg bg-slate-50 p-4">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-emerald-100 text-emerald-800"><BellRing className="size-4" /></span>
              <div>
                <p className="text-sm font-semibold">Decision change</p>
                <p className="mt-0.5 text-sm leading-5 text-slate-600">When the latest decision differs from the previous one → Notify me.</p>
              </div>
            </div>
          </div>
        </Panel>
      </section>
    </div>
  )
}