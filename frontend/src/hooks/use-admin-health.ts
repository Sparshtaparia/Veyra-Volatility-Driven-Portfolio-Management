import { useQuery } from "@tanstack/react-query"
import { adminApi, type ApiHealth, type SystemStatusResponse } from "@/api/admin"

export function useAdminHealth() {
  return useQuery<ApiHealth, Error>({
    queryKey: ["admin", "health"],
    queryFn: () => adminApi.health(),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 15000,
  })
}

export function useSystemStatus() {
  return useQuery<SystemStatusResponse, Error>({
    queryKey: ["admin", "system-status"],
    queryFn: () => adminApi.systemStatus(),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 15000,
  })
}
