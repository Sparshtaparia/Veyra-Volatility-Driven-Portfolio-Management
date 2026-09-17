import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { portfolioApi, type AddHoldingInput, type CreatePortfolioInput } from "@/api/portfolios"

const portfolioKey = "veyra-demo-portfolio-id"
export const getSavedPortfolioId = () => localStorage.getItem(portfolioKey)
export const savePortfolioId = (id: string) => localStorage.setItem(portfolioKey, id)

export function usePortfolio(portfolioId: string | null) { return useQuery({ queryKey: ["portfolio", portfolioId], queryFn: () => portfolioApi.get(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
export function useHoldings(portfolioId: string | null) { return useQuery({ queryKey: ["holdings", portfolioId], queryFn: () => portfolioApi.listHoldings(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
export function useCreatePortfolio() { return useMutation({ mutationFn: (input: CreatePortfolioInput) => portfolioApi.create(input), onSuccess: (portfolio) => { localStorage.setItem(portfolioKey, portfolio.portfolio_id) } }) }
export function useAddHolding(portfolioId: string | null) { const queryClient = useQueryClient(); return useMutation({ mutationFn: (input: AddHoldingInput) => portfolioApi.addHolding(portfolioId!, input), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] }); queryClient.invalidateQueries({ queryKey: ["holdings", portfolioId] }) } }) }
export function useEvaluatePortfolio(portfolioId: string | null) { const queryClient = useQueryClient(); return useMutation({ mutationFn: () => portfolioApi.evaluate(portfolioId!), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["evaluations", portfolioId] }) } }) }
export function useEvaluations(portfolioId: string | null) { return useQuery({ queryKey: ["evaluations", portfolioId], queryFn: () => portfolioApi.listEvaluations(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
export function useEvaluation(portfolioId: string | null, evaluationId: string | null) { return useQuery({ queryKey: ["evaluation", evaluationId], queryFn: () => portfolioApi.getEvaluation(portfolioId!, evaluationId!), enabled: Boolean(portfolioId && evaluationId), retry: false }) }
export function useExecuteRebalance(portfolioId: string | null) { const queryClient = useQueryClient(); return useMutation({ mutationFn: ({ evaluationId, asOfDate }: { evaluationId: string; asOfDate: string }) => portfolioApi.executeRebalance(portfolioId!, evaluationId, asOfDate), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["feedback", portfolioId] }); queryClient.invalidateQueries({ queryKey: ["evaluations", portfolioId] }) } }) }
export function useFeedback(portfolioId: string | null) { return useQuery({ queryKey: ["feedback", portfolioId], queryFn: () => portfolioApi.getFeedback(portfolioId!), enabled: Boolean(portfolioId), retry: false }) }
