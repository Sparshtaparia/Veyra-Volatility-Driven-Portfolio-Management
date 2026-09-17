import { apiFetch } from "./client"

export interface PerformanceStats {
  portfolio_value: number
  invested_amount: number
  absolute_return: number
  return_percentage: number | null
}

export interface RiskScoreComponent {
  score: number
  label: string
}

export interface RiskAssessment {
  overall_score: number | null
  label: string
  components: Record<string, RiskScoreComponent>
  explanations: string[]
}

export interface ConcentrationMetrics {
  largest_position: number | null
  top_3: number | null
  hhi: number | null
}

export interface SnapshotDataPoint {
  date: string
  portfolio_value: number
}

export interface RecentDecision {
  date: string
  action: string
  asset: string
  weight_change: number
  reason: string
}

export interface AdaptiveThresholdState {
  previous: number
  observed: number
  updated: number
  change: number
}

export interface DataStats {
  portfolio_valuations: number
  holdings: number
  transactions: number
  rebalance_evaluations: number
  history_days: number
  last_updated: string | null
}

export interface AnalyticsDashboardResponse {
  portfolio_id: string
  performance: PerformanceStats
  risk_assessment: RiskAssessment | null
  concentration: ConcentrationMetrics
  volatility: number | null
  max_drawdown: number | null
  performance_history: SnapshotDataPoint[]
  recent_decisions: RecentDecision[]
  adaptive_threshold: AdaptiveThresholdState | null
  data_stats: DataStats
}

export const analyticsApi = {
  getDashboard: (portfolioId: string) =>
    apiFetch<AnalyticsDashboardResponse>(`/portfolios/${portfolioId}/analytics/dashboard`),
}
