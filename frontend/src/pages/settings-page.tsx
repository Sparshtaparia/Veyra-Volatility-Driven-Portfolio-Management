import { useState, useEffect } from "react"
import { Check, LoaderCircle } from "lucide-react"
import { useAuth } from "@/auth/auth-context"
import { usePortfolio, useUpdatePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { EmptyState, Field, Notice, Panel, PanelHeader, PrimaryButton, SelectInput, TextInput } from "@/components/ui/primitives"
import { Link } from "react-router-dom"

export function SettingsPage() {
  const { user } = useAuth()
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const updatePortfolio = useUpdatePortfolio(portfolioId)
  
  const [frequency, setFrequency] = useState("Monthly")
  const [maxAllocation, setMaxAllocation] = useState("40")
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (portfolio.data?.max_weight_constraint) {
      setMaxAllocation((portfolio.data.max_weight_constraint * 100).toString())
    }
  }, [portfolio.data])

  if (!portfolioId || !portfolio.data) {
    return <EmptyState title="No portfolio" text="Create a portfolio to configure preferences." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />
  }

  const handleSave = () => {
    updatePortfolio.mutate(
      { 
        name: portfolio.data.name, 
        currency: portfolio.data.currency, 
        max_weight_constraint: parseFloat(maxAllocation) / 100 
      },
      { onSuccess: () => setSaved(true) }
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <p className="text-sm font-semibold text-emerald-700">SETTINGS</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Your account, portfolio and risk preferences.</p>
      </header>

      <section className="mt-6 space-y-6">
        <Panel>
          <PanelHeader title="Account" />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Name"><TextInput value={user?.name ?? ""} readOnly /></Field>
            <Field label="Email"><TextInput value={user?.email ?? ""} readOnly /></Field>
          </div>
          <p className="px-6 pb-5 text-xs text-slate-400">Account details are managed by your authentication provider.</p>
        </Panel>

        <Panel>
          <PanelHeader title="Portfolio preferences" />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Portfolio name"><TextInput value={portfolio.data.name} readOnly /></Field>
            <Field label="Evaluation frequency">
              <SelectInput value={frequency} onChange={(e) => { setFrequency(e.target.value); setSaved(false) }}>
                <option>Monthly</option>
                <option>Weekly</option>
                <option>Quarterly</option>
              </SelectInput>
            </Field>
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Risk preferences" subtitle="Simple guardrails Veyra respects when recommending changes." />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Max allocation per asset (%)">
              <TextInput value={maxAllocation} onChange={(e) => { setMaxAllocation(e.target.value); setSaved(false) }} type="number" min="5" max="100" />
            </Field>
          </div>
          <p className="px-6 pb-4 text-xs leading-5 text-slate-400">
            Veyra's internal methodology — volatility estimation, signal rules, reliability weighting, composite risk and the optimizer — is fixed system configuration and is not exposed here.
          </p>
        </Panel>

        <div className="flex items-center gap-4">
          <PrimaryButton onClick={handleSave} disabled={updatePortfolio.isPending}>
            {updatePortfolio.isPending ? <><LoaderCircle className="size-4 animate-spin mr-2 inline" /> Saving...</> : "Save preferences"}
          </PrimaryButton>
          {saved && <p className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700"><Check className="size-4" /> Saved</p>}
        </div>
        {(portfolio.error || updatePortfolio.error) && <Notice text={portfolio.error?.message || updatePortfolio.error?.message || "An error occurred"} />}
      </section>
    </div>
  )
}