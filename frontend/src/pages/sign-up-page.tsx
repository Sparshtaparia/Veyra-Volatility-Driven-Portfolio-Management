import { useState } from "react"
import {
  ArrowRight,
  BadgeCheck,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  TrendingUp,
  User,
} from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/auth-context"

export function SignUpPage() {
  const navigate = useNavigate()
  const { createInvestor } = useAuth()
  const [form, setForm] = useState({ name: "", email: "", password: "" })
  const [showPwd, setShowPwd] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    if (!form.email.includes("@")) { setError("Enter a valid email address."); return }
    if (form.password.length < 8)  { setError("Password must be at least 8 characters."); return }
    setPending(true)
    try {
      await createInvestor(form.name, form.email, form.password)
      navigate("/onboarding")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create your account.")
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Left dark panel */}
      <aside className="hidden w-[45%] shrink-0 flex-col justify-between bg-[#0f1f0f] p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Veyra Logo" className="size-8" />
          <span className="font-bold text-white">Veyra</span>
        </div>

        <div>
          <h2 className="text-3xl font-black leading-tight text-white">
            Start your<br />
            <span className="text-emerald-400">smarter investing</span><br />
            journey today.
          </h2>
          <ul className="mt-8 space-y-4">
            {[
              { icon: <ShieldCheck className="size-4" />, text: "Risk-aware portfolio signals" },
              { icon: <TrendingUp  className="size-4" />, text: "Volatility-driven rebalancing" },
              { icon: <BadgeCheck  className="size-4" />, text: "No real trades executed" },
            ].map((f) => (
              <li key={f.text} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-emerald-900 text-emerald-400">{f.icon}</span>
                {f.text}
              </li>
            ))}
          </ul>
        </div>

        <p className="font-serif italic text-sm text-slate-400">
          "Better decisions today. A more resilient tomorrow."
        </p>
      </aside>

      {/* Right white panel */}
      <main className="flex flex-1 flex-col items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <img src="/logo.png" alt="Veyra Logo" className="size-8" />
            <span className="font-bold text-slate-900">Veyra</span>
          </div>

          <h1 className="text-2xl font-black text-slate-900">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500">It only takes a minute to get started.</p>

          <form onSubmit={submit} className="mt-7 space-y-4" noValidate>
            <div>
              <label htmlFor="su-name" className="block text-xs font-semibold text-slate-700 mb-1.5">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <input id="su-name" type="text" value={form.name} onChange={set("name")} placeholder="Enter your full name"
                  className="h-11 w-full rounded-xl border border-slate-200 pl-9 pr-3 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 transition" />
              </div>
            </div>
            <div>
              <label htmlFor="su-email" className="block text-xs font-semibold text-slate-700 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <input id="su-email" type="email" value={form.email} onChange={set("email")} placeholder="you@example.com" required autoComplete="off"
                  className="h-11 w-full rounded-xl border border-slate-200 pl-9 pr-3 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 transition" />
              </div>
            </div>
            <div>
              <label htmlFor="su-password" className="block text-xs font-semibold text-slate-700 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <input id="su-password" type={showPwd ? "text" : "password"} value={form.password} onChange={set("password")} placeholder="At least 8 characters" required autoComplete="new-password"
                  className="h-11 w-full rounded-xl border border-slate-200 pl-9 pr-10 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-100 transition" />
                <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition">
                  {showPwd ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>
            <label className="flex cursor-pointer items-start gap-2.5 text-xs text-slate-600">
              <input type="checkbox" required className="mt-0.5 size-4 accent-emerald-600" />
              I agree to Veyra's Terms of Use and Privacy Policy.
            </label>
            {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</p>}
            <button type="submit" disabled={pending}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60 transition">
              {pending ? "Creating account…" : <><span>Create account</span><ArrowRight className="size-4" /></>}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/sign-in" className="font-semibold text-emerald-700 hover:underline">Sign in</Link>
          </p>
        </div>
      </main>
    </div>
  )
}
