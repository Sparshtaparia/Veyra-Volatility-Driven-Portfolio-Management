import { useState } from "react"
import { Navigate } from "react-router-dom"

import { useAuth } from "@/auth/auth-model"
import { AuthShell } from "@/components/auth/auth-shell"
import { FormField } from "@/components/auth/form-field"

export function ResetPasswordPage() {
  const { user, loading, updatePassword } = useAuth()
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [updated, setUpdated] = useState(false)
  const [pending, setPending] = useState(false)

  if (loading) return null
  if (!user && !updated) return <Navigate to="/sign-in" replace />
  if (updated) return <Navigate to="/sign-in" replace />

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password.length < 8) {
      setError("Password must be at least 8 characters.")
      return
    }
    setPending(true)
    setError("")
    try {
      await updatePassword(password)
      setUpdated(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update your password.")
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthShell>
      <h1 className="text-3xl font-semibold tracking-tight">Choose a new password</h1>
      <p className="mt-3 leading-6 text-slate-600">
        Use at least 8 characters. Your recovery session will authorize this one change.
      </p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <FormField
          id="new-password"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={error}
        />
        <button
          type="submit"
          disabled={pending}
          className="h-12 w-full rounded-lg bg-slate-950 text-sm font-semibold text-white disabled:opacity-60"
        >
          {pending ? "Updating…" : "Update password"}
        </button>
      </form>
    </AuthShell>
  )
}
