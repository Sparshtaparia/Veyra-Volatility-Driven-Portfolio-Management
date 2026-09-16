import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { portfolioApi, type AddHoldingInput, type CreatePortfolioInput } from "@/api/portfolios"

const portfolioKey = "veyra-demo-portfolio-id"
export const getSavedPortfolioId = () => localStorage.getItem(portfolioKey)

export function usePortfolio(portfolioId: string | null) { return useQuery({ queryKey: ["portfolio", portfolioId], queryFn: () => portfolioApi.get(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
export function useHoldings(portfolioId: string | null) { return useQuery({ queryKey: ["holdings", portfolioId], queryFn: () => portfolioApi.listHoldings(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
export function useCreatePortfolio() { return useMutation({ mutationFn: (input: CreatePortfolioInput) => portfolioApi.create(input), onSuccess: (portfolio) => { localStorage.setItem(portfolioKey, portfolio.portfolio_id) } }) }
export function useAddHolding(portfolioId: string | null) { const queryClient = useQueryClient(); return useMutation({ mutationFn: (input: AddHoldingInput) => portfolioApi.addHolding(portfolioId!, input), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] }); queryClient.invalidateQueries({ queryKey: ["holdings", portfolioId] }) } }) }
export function useEvaluatePortfolio(portfolioId: string | null) { return useMutation({ mutationFn: () => portfolioApi.evaluate(portfolioId!) }) }
export function useEvaluation(portfolioId: string | null, evaluationId: string | null) { return useQuery({ queryKey: ["evaluation", evaluationId], queryFn: () => portfolioApi.getEvaluation(portfolioId!, evaluationId!), enabled: Boolean(portfolioId && evaluationId), retry: false }) }
