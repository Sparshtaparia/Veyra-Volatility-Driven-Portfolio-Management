import { useState, useEffect } from "react"
import { Plus, Settings } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useHoldings, usePortfolio, useUpdatePortfolio, useDeletePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { currency } from "@/lib/format"
import { PortfolioDonut, AllocationLegend } from "@/components/portfolio/portfolio-chart"
import { HoldingsTable } from "@/components/portfolio/holdings-table"
import { AddHoldingForm } from "@/components/portfolio/holding-form"
import { Loading, Notice, OutlineButton, Panel, EmptyState, Field, TextInput } from "@/components/ui/primitives"

export function PortfolioPage() {
  const navigate = useNavigate()
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const updatePortfolio = useUpdatePortfolio(portfolioId)
  const deletePortfolio = useDeletePortfolio(portfolioId)
  
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState("")
  const [editCurrency, setEditCurrency] = useState("")

  useEffect(() => {
    if (portfolio.data) {
      setEditName(portfolio.data.name)
      setEditCurrency(portfolio.data.currency)
    }
  }, [portfolio.data])

  useEffect(() => {
    if (deletePortfolio.isSuccess) {
      navigate("/onboarding")
    }
  }, [deletePortfolio.isSuccess, navigate])

  if (!portfolioId) return <EmptyState title="No portfolio yet" text="Create a portfolio through onboarding before managing it." action={<Link to="/onboarding" className="inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Set up a portfolio</Link>} />

  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-emerald-700">PORTFOLIO</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">{portfolio.data?.name ?? "My Portfolio"}</h1>
          {portfolio.data && <p className="mt-1 text-sm text-slate-500">{currency(portfolio.data.total_value, portfolio.data.currency)}</p>}
        </div>
        <div className="flex gap-3">
          <OutlineButton onClick={() => setAdding((v) => !v)}><Plus className="size-4" /> Add Holding</OutlineButton>
          <OutlineButton onClick={() => setEditing(true)}><Settings className="size-4" /> Edit Portfolio</OutlineButton>
        </div>
      </header>

      {editing && portfolio.data && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Edit Portfolio</h2>
              <button onClick={() => setEditing(false)} className="text-slate-400 hover:text-slate-600">×</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); updatePortfolio.mutate({ name: editName, currency: editCurrency }, { onSuccess: () => setEditing(false) }) }} className="mt-6 space-y-4">
              <Field label="Portfolio Name">
                <TextInput value={editName} onChange={e => setEditName(e.target.value)} required />
              </Field>
              <Field label="Base Currency">
                <TextInput value={editCurrency} onChange={e => setEditCurrency(e.target.value)} required />
              </Field>
              <div className="mt-8 flex items-center gap-3">
                <button type="submit" disabled={updatePortfolio.isPending} className="flex-1 rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
                  {updatePortfolio.isPending ? "Saving..." : "Save Changes"}
                </button>
                <button type="button" onClick={() => deletePortfolio.mutate()} disabled={deletePortfolio.isPending} className="rounded-lg bg-red-100 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-200 disabled:opacity-60">
                  {deletePortfolio.isPending ? "Deleting..." : "Delete"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {portfolio.error && <Notice text={portfolio.error.message} />}

      {portfolio.isLoading ? (
        <Loading label="Loading portfolio…" />
      ) : (
        <>
          {adding && (
            <div className="mt-6">
              <AddHoldingForm portfolioId={portfolioId} onAdded={() => setAdding(false)} />
            </div>
          )}

          <section className="mt-6 grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
            <Panel className="p-6">
              <h2 className="text-base font-semibold text-slate-950">Allocation</h2>
              <div className="mt-4 flex justify-center">
                {holdings.data?.length ? (
                  <PortfolioDonut holdings={holdings.data} />
                ) : (
                  <p className="py-10 text-sm text-slate-500">Add holdings to see your allocation.</p>
                )}
              </div>
              {holdings.data?.length ? (
                <div className="mt-6 max-w-xs mx-auto"><AllocationLegend holdings={holdings.data} /></div>
              ) : null}
            </Panel>

            <Panel>
              <div className="border-b border-slate-100 px-6 py-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-slate-950">Holdings</h2>
                  <p className="text-sm text-slate-500">{holdings.data?.length ?? 0} assets</p>
                </div>
              </div>
              {holdings.isLoading ? (
                <Loading label="Loading holdings…" />
              ) : holdings.data?.length ? (
                <div className="px-6 py-4"><HoldingsTable holdings={holdings.data} portfolioId={portfolioId!} /></div>
              ) : (
                <EmptyState title="No holdings yet" text="Add your first holding to see it in the portfolio." action={<button onClick={() => setAdding(true)} className="inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white"><Plus className="size-4" /> Add Holding</button>} />
              )}
            </Panel>
          </section>

          {holdings.data && holdings.data.length > 0 && (
            <p className="mt-4 text-xs text-slate-400">Prices and weights reflect the latest market data available to Veyra.</p>
          )}
        </>
      )}
    </div>
  )
}