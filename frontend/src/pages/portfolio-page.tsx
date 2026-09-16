import { useState } from "react"
import { Plus, Settings } from "lucide-react"
import { Link } from "react-router-dom"
import { useHoldings, usePortfolio } from "@/hooks/use-portfolio"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { currency } from "@/lib/format"
import { PortfolioDonut, AllocationLegend } from "@/components/portfolio/portfolio-chart"
import { HoldingsTable } from "@/components/portfolio/holdings-table"
import { AddHoldingForm } from "@/components/portfolio/holding-form"
import { Loading, Notice, OutlineButton, Panel, EmptyState } from "@/components/ui/primitives"

export function PortfolioPage() {
  const portfolioId = getSavedPortfolioId()
  const portfolio = usePortfolio(portfolioId)
  const holdings = useHoldings(portfolioId)
  const [adding, setAdding] = useState(false)

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
          <Link to="/app/settings" className="inline-flex h-11 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50"><Settings className="size-4" /> Edit Portfolio</Link>
        </div>
      </header>

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
                <div className="px-6 py-4"><HoldingsTable holdings={holdings.data} /></div>
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