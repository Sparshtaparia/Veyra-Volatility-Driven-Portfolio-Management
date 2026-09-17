import { useState } from "react"
import { ArrowRight, BarChart2, Eye, EyeOff, Lock, Mail, RefreshCw, ShieldCheck, TrendingUp } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { portfolioApi } from "@/api/portfolios"
import { useAuth } from "@/auth/auth-model"
import { savePortfolioId } from "@/hooks/use-portfolio"

// ─── Left panel ────────────────────────────────────────────────────────────

function AuthLeftPanel() {
  return (
    <div className="relative hidden h-full flex-col justify-between overflow-hidden bg-[#0f1f0f] p-10 text-white lg:flex">
      {/* Subtle mountain texture via gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_80%,rgba(22,163,74,0.25),transparent)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,transparent_50%,rgba(0,0,0,0.55))]" />

      {/* Logo */}
      <div className="relative flex items-center gap-2.5">
        <span className="grid size-8 place-items-center rounded-md bg-emerald-600 text-sm font-bold text-white">V</span>
        <div>
          <p className="font-bold">Veyra</p>
          <p className="text-[10px] text-emerald-300/70">Smarter Portfolios for a Volatile World.</p>
        </div>
      </div>

      {/* Headline */}
      <div className="relative">
        <h1 className="text-3xl font-bold leading-tight sm:text-4xl">
          Disciplined investing
          <br />
          <span className="text-emerald-400">for a changing world.</span>
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-300">
          Veyra uses quantitative intelligence to evaluate, optimize, and adapt your portfolio — so
          you can focus on what matters most.
        </p>

        {/* Feature bullets */}
        <ul className="mt-7 space-y-3">
          {[
            { icon: <BarChart2 className="size-4" />, title: "Market Aware", sub: "Understands volatility, regimes and risk factors." },
            { icon: <ShieldCheck className="size-4" />, title: "Data Driven", sub: "Objective, quantitative portfolio decisions." },
            { icon: <RefreshCw className="size-4" />, title: "Adaptive", sub: "Tells you when to rebalance, not every day." },
            { icon: <TrendingUp className="size-4" />, title: "Portfolio Focused", sub: "Built for long-term, resilient wealth creation." },
          ].map((f) => (
            <li key={f.title} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white/10 text-emerald-300">
                {f.icon}
              </span>
              <div>
                <p className="text-sm font-semibold">{f.title}</p>
                <p className="text-xs text-slate-400">{f.sub}</p>
              </div>
            </li>
          ))}
        </ul>

        {/* Mini portfolio card */}
        <div className="mt-8 overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <p className="text-xs text-slate-400">Portfolio Value</p>
          <p className="mt-0.5 text-2xl font-black tabular-nums">₹12,48,320</p>
          <p className="text-xs text-emerald-400">▲ +4.82% (Past 3 Months)</p>
          <div className="absolute -right-4 top-3">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-900/50 px-3 py-1.5 text-[10px]">
              <p className="font-bold text-emerald-300">Veyra Decision · HOLD</p>
              <p className="text-slate-400">Last evaluated · 17 Sep 2026</p>
            </div>
          </div>
        </div>

        <p className="mt-6 font-serif italic text-slate-400">"A more resilient tomorrow."</p>
      </div>
    </div>
  )
}

// ─── Sign-in page ──────────────────────────────────────────────────────────

export function SignInPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const { signIn } = useAuth()
  const navigate = useNavigate()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setPending(true)
    try {
      const user = await signIn(email, password)
      if (user.role === "ADMIN") {
        navigate("/admin")
        return
      }
      const portfolios = await portfolioApi.list()
      if (portfolios.length === 0) {
        navigate("/onboarding")
      } else {
        savePortfolioId(portfolios[0].portfolio_id)
        navigate("/app")
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to sign in.")
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-white">
      {/* Left panel — 45% */}
      <div className="relative w-[45%] shrink-0">
        <AuthLeftPanel />
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 flex-col">
        <div className="flex justify-end p-5">
          <span className="text-sm text-slate-500">Don't have an account?</span>
          <Link to="/sign-up" className="ml-2 rounded-lg border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition">
            Sign Up
          </Link>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center px-8 py-10">
          <div className="w-full max-w-md">
            {/* Logo */}
            <div className="flex items-center justify-center gap-2 mb-6">
              <span className="grid size-8 place-items-center rounded-md bg-[#14532d] text-sm font-bold text-white">V</span>
              <span className="font-bold text-slate-900">Veyra</span>
            </div>

            <h2 className="text-center text-2xl font-bold text-slate-900">Welcome back</h2>
            <p className="mt-1 text-center text-sm text-slate-500">Sign in to continue to your portfolio</p>

            <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
              {/* Email */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5" htmlFor="email">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                  <input
                    id="email" type="email" required value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@domain.com"
                    className="h-11 w-full rounded-xl border border-slate-200 pl-10 pr-4 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100 transition"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                  <input
                    id="password" type={showPw ? "text" : "password"} required
                    value={password} onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="h-11 w-full rounded-xl border border-slate-200 pl-10 pr-10 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                  >
                    {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                <div className="mt-1.5 flex justify-end">
                  <Link to="/forgot-password" className="text-xs font-semibold text-emerald-700 hover:underline">
                    Forgot password?
                  </Link>
                </div>
              </div>

              {error && (
                <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={pending}
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                {pending ? "Signing in…" : <><span>Sign In</span><ArrowRight className="size-4" /></>}
              </button>
            </form>

            {/* OR divider */}
            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-semibold text-slate-400">OR</span>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            {/* Social (UI only) */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                className="flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>
              <button
                type="button"
                className="flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" fill="#24292e"/>
                </svg>
                Continue with GitHub
              </button>
            </div>

            <p className="mt-6 text-center text-xs text-slate-400">
              By signing in, you agree to our{" "}
              <a href="#" className="text-emerald-700 hover:underline">Terms of Service</a>
              {" "}and{" "}
              <a href="#" className="text-emerald-700 hover:underline">Privacy Policy</a>.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
