import { apiFetch } from "@/api/client"

export type Portfolio = { portfolio_id: string; name: string; currency: string; total_value: number; created_at: string }
export type Holding = { id: number; ticker: string; quantity: number; average_price: number; current_price: number; market_value: number; weight: number }
export type Evaluation = { evaluation_id: string; portfolio_id: string; evaluation_date: string; trigger: string; decision: string; status: string; created_at: string }
export type SignalDecision = { evaluation_id: string; portfolio_id: string; as_of_date: string; composite_risk?: { composite_score: number; risk_state: string; components: { volatility_exposure: number; concentration: number } }; controls: Array<{ ticker: string; base_signal: number; regulated_signal: number; attenuation_factor: number; control_output: number; direction: string; decision_state: "HOLD" | "REVIEW" | "ADAPT"; regime: string; volatility_state: number; risk_state: string; reliability_state: string; reason_codes: string[] }>; allocation_result?: { allocations: Array<{ ticker: string; current_weight: number; target_weight: number; delta_weight: number }>; total_turnover: number; decision: string } }
export type CreatePortfolioInput = { name: string; currency: string }
export type AddHoldingInput = { ticker: string; quantity: number; average_price: number; current_price: number }
export type FeedbackData = {
  portfolio_id: string
  previous_threshold: number
  observed_volatility: number
  feedback_error: number
  updated_threshold: number
  timestamp: string
}

export const portfolioApi = {
  create: (input: CreatePortfolioInput) => apiFetch<Portfolio>("/portfolios", { method: "POST", body: JSON.stringify(input) }),
  get: (portfolioId: string) => apiFetch<Portfolio>(`/portfolios/${portfolioId}`),
  listHoldings: (portfolioId: string) => apiFetch<Holding[]>(`/portfolios/${portfolioId}/holdings`),
  addHolding: (portfolioId: string, input: AddHoldingInput) => apiFetch<Holding>(`/portfolios/${portfolioId}/holdings`, { method: "POST", body: JSON.stringify(input) }),
  evaluate: (portfolioId: string) => apiFetch<SignalDecision>(`/portfolios/${portfolioId}/signals/evaluate`, { method: "POST", body: JSON.stringify({ as_of_date: new Date().toISOString().slice(0, 10) }) }),
  getEvaluation: (portfolioId: string, evaluationId: string) => apiFetch<Evaluation>(`/portfolios/${portfolioId}/evaluations/${evaluationId}`),
  executeRebalance: (portfolioId: string) => apiFetch<any>(`/portfolios/${portfolioId}/rebalance`, { method: "POST", body: JSON.stringify({ as_of_date: new Date().toISOString().slice(0, 10) }) }),
  getFeedback: (portfolioId: string) => apiFetch<FeedbackData | null>(`/portfolios/${portfolioId}/feedback`),
}
