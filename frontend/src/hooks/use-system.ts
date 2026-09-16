import { useQuery } from "@tanstack/react-query"
import { systemApi } from "@/api/system"

export function useSystemStatus() {
  return useQuery({ queryKey: ["system-status"], queryFn: () => systemApi.status(), retry: false, refetchInterval: 30000 })
}