import { useState } from "react"
import { ArrowLeft, MailCheck } from "lucide-react"
import { Link } from "react-router-dom"
import { AuthShell } from "@/components/auth/auth-shell"
import { FormField } from "@/components/auth/form-field"

export function ForgotPasswordPage() {
  const [email, setEmail] = useState(""); const [sent, setSent] = useState(false); const [error, setError] = useState("")
  function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); if (!email.includes("@")) { setError("Enter the email address linked to your account."); return } setError(""); setSent(true) }
  return <AuthShell>{sent ? <div className="text-center"><span className="mx-auto grid size-12 place-items-center rounded-full bg-emerald-100 text-emerald-700"><MailCheck className="size-6" /></span><h1 className="mt-5 text-3xl font-semibold tracking-tight">Check your inbox</h1><p className="mt-3 leading-6 text-slate-600">If an account uses <strong>{email}</strong>, we’ll send password-reset instructions shortly.</p><Link to="/sign-in" className="mt-8 inline-flex h-11 items-center rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white">Back to sign in</Link></div> : <><Link to="/sign-in" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950"><ArrowLeft className="size-4" /> Back to sign in</Link><h1 className="mt-7 text-3xl font-semibold tracking-tight">Reset your password</h1><p className="mt-3 leading-6 text-slate-600">Enter your email and we’ll send you a link to choose a new password.</p><form onSubmit={submit} className="mt-8 space-y-5" noValidate><FormField id="email" label="Email address" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} error={error} /><button type="submit" className="h-12 w-full rounded-lg bg-slate-950 text-sm font-semibold text-white transition hover:bg-slate-800">Send reset link</button></form></>}</AuthShell>
}
