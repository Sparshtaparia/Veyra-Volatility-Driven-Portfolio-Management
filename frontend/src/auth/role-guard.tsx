import { Navigate } from "react-router-dom"
import { type Role, useAuth } from "@/auth/auth-model"

export function RoleGuard({ role, children }: { role: Role; children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/sign-in" replace />
  if (user.role !== role) return <Navigate to="/403" replace />
  return <>{children}</>
}
