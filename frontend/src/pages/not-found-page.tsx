import { ArrowLeft, Home } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f6f7] px-6 text-center">
      {/* Veyra logo mark */}
      <span className="grid size-14 place-items-center rounded-2xl bg-[#14532d] text-xl font-black text-white shadow-lg">
        V
      </span>

      {/* Large number */}
      <p className="mt-8 text-[7rem] font-black leading-none text-slate-200 select-none">404</p>

      <h1 className="mt-2 text-2xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500 max-w-xs">
        The page you're looking for doesn't exist or may have been moved.
      </p>

      <div className="mt-8 flex gap-3">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ArrowLeft className="size-4" /> Go Back
        </button>
        <Link
          to="/app"
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 transition"
        >
          <Home className="size-4" /> Dashboard
        </Link>
      </div>

      <p className="mt-12 text-xs text-slate-400">Veyra · Volatility-Driven Portfolio Management</p>
    </div>
  )
}
