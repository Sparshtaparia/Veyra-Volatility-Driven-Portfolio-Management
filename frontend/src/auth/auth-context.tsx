import { useEffect, useMemo, useState } from "react"
import { authErrorMessage } from "@/auth/auth-errors"
import { AuthContext, type AuthContextValue, type CurrentUser } from "@/auth/auth-model"
import { supabase } from "@/lib/supabase"

function toCurrentUser(user: {
  id: string
  email?: string
  user_metadata?: Record<string, unknown>
  app_metadata?: Record<string, unknown>
}): CurrentUser {
  const metadata = user.user_metadata ?? {}
  const appMetadata = user.app_metadata ?? {}
  return {
    id: user.id,
    email: user.email ?? "",
    name: String(metadata.full_name ?? metadata.name ?? user.email?.split("@")[0] ?? "Investor"),
    role: appMetadata.role === "ADMIN" ? "ADMIN" : "INVESTOR",
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (error) console.warn("Unable to restore Supabase session")
        setUser(data.session?.user ? toCurrentUser(data.session.user) : null)
      })
      .finally(() => setLoading(false))

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (
        event === "SIGNED_IN" ||
        event === "SIGNED_OUT" ||
        event === "TOKEN_REFRESHED" ||
        event === "USER_UPDATED" ||
        event === "PASSWORD_RECOVERY"
      ) {
        setUser(session?.user ? toCurrentUser(session.user) : null)
        setLoading(false)
      }
    })
    return () => listener.subscription.unsubscribe()
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signIn: async (email, password) => {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw new Error(authErrorMessage(error))
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
        if (sessionError || !sessionData.session || !data.user) {
          throw new Error(
            sessionError ? authErrorMessage(sessionError) : "Unable to establish a secure session.",
          )
        }
        const currentUser = toCurrentUser(data.user)
        setUser(currentUser)
        return currentUser
      },
      createInvestor: async (name, email, password) => {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: name } },
        })
        if (error) throw new Error(authErrorMessage(error))
        if (!data.session) return "confirmation_required"
        if (data.user) setUser(toCurrentUser(data.user))
        return "authenticated"
      },
      resendConfirmation: async (email) => {
        const { error } = await supabase.auth.resend({ type: "signup", email })
        if (error) throw new Error(authErrorMessage(error))
      },
      resetPassword: async (email) => {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        })
        if (error) throw new Error(authErrorMessage(error))
      },
      updatePassword: async (password) => {
        const { error } = await supabase.auth.updateUser({ password })
        if (error) throw new Error(authErrorMessage(error))
      },
      signOut: async () => {
        const { error } = await supabase.auth.signOut()
        if (error) throw new Error(authErrorMessage(error))
        setUser(null)
      },
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
