import { useState } from "react"
import { ArrowRight } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/auth-context"
import { AuthShell } from "@/components/auth/auth-shell"
import { FormField } from "@/components/auth/form-field"

export function SignInPage() {
  const navigate = useNavigate(); const { signIn } = useAuth(); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState("")
  function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); const user = signIn(email, password); if (!user) { setError("Enter a valid email address and password to continue."); return } navigate(user.role === "ADMIN" ? "/admin" : "/app") }
  return <AuthShell><p className="text-sm font-medium text-emerald-700">Welcome back</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Sign in to Veyra</h1><p className="mt-3 leading-6 text-slate-600">Pick up where you left off with a clear view of your investments.</p><form onSubmit={submit} className="mt-8 space-y-5" noValidate><FormField id="email" label="Email address" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} /><div><FormField id="password" label="Password" type="password" autoComplete="current-password" placeholder="Your password" value={password} onChange={(event) => setPassword(event.target.value)} /><Link to="/forgot-password" className="mt-2 inline-block text-sm font-semibold text-emerald-700 hover:text-emerald-800">Forgot password?</Link></div>{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button type="submit" className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 text-sm font-semibold text-white transition hover:bg-slate-800">Sign in <ArrowRight className="size-4" /></button></form><p className="mt-6 text-center text-sm text-slate-600">New to Veyra? <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to="/sign-up">Create an account</Link></p></AuthShell>
}
