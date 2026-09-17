import { apiFetch } from "@/api/client"

export type Portfolio = { portfolio_id: string; name: string; currency: string; total_value: number; max_weight_constraint: number; created_at: string; updated_at?: string }
export type Holding = { id: number; ticker: string; quantity: number; average_price: number; current_price: number; market_value: number; weight: number }
export type Evaluation = { evaluation_id: string; portfolio_id: string; evaluation_date: string; trigger: string; decision: string; status: string; created_at: string }
export type SignalDecision = { evaluation_id: string; portfolio_id: string; as_of_date: string; composite_risk?: { composite_score: number; risk_state: string; components: { volatility_exposure: number; concentration: number } }; controls: Array<{ ticker: string; base_signal: number; regulated_signal: number; attenuation_factor: number; control_output: number; direction: string; decision_state: "HOLD" | "REVIEW" | "ADAPT"; regime: string; volatility_state: number; risk_state: string; reliability_state: string; reason_codes: string[] }>; allocation_result?: { allocations: Array<{ ticker: string; current_weight: number; target_weight: number; delta_weight: number }>; total_turnover: number; decision: string } }
export type CreatePortfolioInput = { name: string; currency: string; max_weight_constraint?: number }
export type AddHoldingInput = { ticker: string; quantity: number; average_price: number; current_price: number }
export type FeedbackData = {
  portfolio_id: string
  previous_threshold: number
  observed_volatility: number
  feedback_error: number
  updated_threshold: number
  timestamp: string
}
export type PaperOrder = { ticker: string; side: "BUY" | "SELL"; quantity: number; execution_price: number; transaction_cost: number; slippage_cost: number; status: string }
export type PaperExecution = { evaluation_id: string; portfolio_id: string; orders: PaperOrder[]; execution_time: string; total_cost: number; simulated_holdings: Array<{ ticker: string; quantity: number; market_value?: number; weight: number }> }

export const portfolioApi = {
  create: (input: CreatePortfolioInput) => apiFetch<Portfolio>("/portfolios", { method: "POST", body: JSON.stringify(input) }),
  update: (portfolioId: string, input: { name: string; currency: string; max_weight_constraint?: number }) => apiFetch<Portfolio>(`/portfolios/${portfolioId}`, { method: "PUT", body: JSON.stringify(input) }),
  delete: (portfolioId: string) => apiFetch<void>(`/portfolios/${portfolioId}`, { method: "DELETE" }),
  get: (portfolioId: string) => apiFetch<Portfolio>(`/portfolios/${portfolioId}`),
  listHoldings: (portfolioId: string) => apiFetch<Holding[]>(`/portfolios/${portfolioId}/holdings`),
  addHolding: (portfolioId: string, input: AddHoldingInput) => apiFetch<Holding>(`/portfolios/${portfolioId}/holdings`, { method: "POST", body: JSON.stringify(input) }),
  updateHolding: (portfolioId: string, ticker: string, input: AddHoldingInput) => apiFetch<Holding>(`/portfolios/${portfolioId}/holdings/${ticker}`, { method: "PUT", body: JSON.stringify(input) }),
  deleteHolding: (portfolioId: string, ticker: string) => apiFetch<void>(`/portfolios/${portfolioId}/holdings/${ticker}`, { method: "DELETE" }),
  evaluate: (portfolioId: string) => apiFetch<SignalDecision>(`/portfolios/${portfolioId}/signals/evaluate`, { method: "POST", body: JSON.stringify({ as_of_date: new Date().toISOString().slice(0, 10) }) }),
  getEvaluation: (portfolioId: string, evaluationId: string) => apiFetch<Evaluation>(`/portfolios/${portfolioId}/evaluations/${evaluationId}`),
  listEvaluations: (portfolioId: string) => apiFetch<Evaluation[]>(`/portfolios/${portfolioId}/evaluations`),
  executeRebalance: (portfolioId: string) => apiFetch<PaperExecution>(`/portfolios/${portfolioId}/rebalance`, { method: "POST", body: JSON.stringify({ as_of_date: new Date().toISOString().slice(0, 10) }) }),
  getFeedback: (portfolioId: string) => apiFetch<FeedbackData | null>(`/portfolios/${portfolioId}/feedback`),
}
