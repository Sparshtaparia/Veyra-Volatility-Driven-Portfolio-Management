import { ArrowLeft, Lock } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

export function ForbiddenPage() {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f6f7] px-6 text-center">
      {/* Icon */}
      <span className="grid size-14 place-items-center rounded-2xl bg-rose-100 text-rose-600 shadow">
        <Lock className="size-7" />
      </span>

      <p className="mt-8 text-[7rem] font-black leading-none text-slate-200 select-none">403</p>

      <h1 className="mt-2 text-2xl font-bold text-slate-900">Access denied</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500 max-w-xs">
        You don't have permission to view this page. Please contact your administrator if you think this is a mistake.
      </p>

      <div className="mt-8 flex gap-3">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ArrowLeft className="size-4" /> Go Back
        </button>
        <Link
          to="/sign-in"
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 transition"
        >
          Sign In
        </Link>
      </div>

      <p className="mt-12 text-xs text-slate-400">Veyra · Volatility-Driven Portfolio Management</p>
    </div>
  )
}
