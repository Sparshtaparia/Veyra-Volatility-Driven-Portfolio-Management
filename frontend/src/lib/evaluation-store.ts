import type { PaperExecution, SignalDecision } from "@/api/portfolios"

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

export function readLatestExecution(portfolioId: string): PaperExecution | null {
  const raw = localStorage.getItem(executionKey(portfolioId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as PaperExecution
  } catch {
    return null
  }
}

export function writeLatestExecution(portfolioId: string, result: PaperExecution) {
  localStorage.setItem(executionKey(portfolioId), JSON.stringify(result))
}
