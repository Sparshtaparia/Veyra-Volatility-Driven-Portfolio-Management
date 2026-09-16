import type { SignalDecision } from "@/api/portfolios"

export type PreviewHolding = { ticker: string; current_price: number; market_value: number }

export type PreviewOrder = {
  ticker: string
  side: "BUY" | "SELL"
  weightChange: number
  notional: number
  shares: number
}

export function previewOrders(result: SignalDecision, holdings: PreviewHolding[]): PreviewOrder[] | null {
  if (!result.allocation_result) return null
  const prices = new Map(holdings.map((h) => [h.ticker.toUpperCase(), h.current_price]))
  const totalValue = holdings.reduce((sum, h) => sum + h.market_value, 0)
  const orders: PreviewOrder[] = []
  for (const alloc of result.allocation_result.allocations) {
    const ticker = alloc.ticker.toUpperCase()
    const notional = alloc.delta_weight * totalValue
    if (Math.abs(notional) < 1) continue
    const price = prices.get(ticker)
    if (!price) {
      orders.push({ ticker, side: notional > 0 ? "BUY" : "SELL", weightChange: alloc.delta_weight, notional, shares: 0 })
      continue
    }
    orders.push({
      ticker,
      side: notional > 0 ? "BUY" : "SELL",
      weightChange: alloc.delta_weight,
      notional,
      shares: Math.abs(notional) / price,
    })
  }
  return orders.length ? orders : null
}

export function previewTurnover(result: SignalDecision): number {
  return result.allocation_result?.total_turnover ?? 0
}