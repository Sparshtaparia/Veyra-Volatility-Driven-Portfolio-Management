import type { SignalDecision } from "@/api/portfolios"

const evaluationKey = (portfolioId: string) => `veyra-latest-evaluation-${portfolioId}`
const executionKey = (portfolioId: string) => `veyra-latest-execution-${portfolioId}`

export function readLatestEvaluation(portfolioId: string): SignalDecision | null {
  const raw = localStorage.getItem(evaluationKey(portfolioId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as SignalDecision
  } catch {
    return null
  }
}

export function writeLatestEvaluation(portfolioId: string, result: SignalDecision) {
  localStorage.setItem(evaluationKey(portfolioId), JSON.stringify(result))
}

export function readLatestExecution(portfolioId: string): PaperExecutionResult | null {
  const raw = localStorage.getItem(executionKey(portfolioId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as PaperExecutionResult
  } catch {
    return null
  }
}

export function writeLatestExecution(portfolioId: string, result: PaperExecutionResult) {
  localStorage.setItem(executionKey(portfolioId), JSON.stringify(result))
}

export type PaperOrder = {
  ticker: string
  side: "BUY" | "SELL"
  quantity: number
  reference_price: number
  execution_price: number
  gross_notional: number
  transaction_cost: number
  slippage_cost: number
  net_cash_change: number
  status?: string
}

export type PaperExecutionResult = {
  evaluation_id: string
  portfolio_id: string
  orders: PaperOrder[]
  simulated_holdings: Array<{ ticker: string; quantity: number; weight: number; market_value: number }>
  total_cost: number
  total_slippage?: number
  transaction_cost?: number
  turnover?: number
}