import { createContext, useContext } from "react"

export type Role = "INVESTOR" | "ADMIN"
export type CurrentUser = { id: string; name: string; email: string; role: Role }
export type SignupOutcome = "authenticated" | "confirmation_required"

export type AuthContextValue = {
  user: CurrentUser | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<CurrentUser>
  createInvestor: (name: string, email: string, password: string) => Promise<SignupOutcome>
  resendConfirmation: (email: string) => Promise<void>
  resetPassword: (email: string) => Promise<void>
  updatePassword: (password: string) => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}

export function useRole() {
  return useAuth().user?.role ?? null
}
