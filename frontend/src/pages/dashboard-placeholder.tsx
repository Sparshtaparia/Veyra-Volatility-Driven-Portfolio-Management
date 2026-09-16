import { Link } from "react-router-dom"

export function DashboardPlaceholder() {
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-6 text-center"><div><p className="text-sm font-semibold text-emerald-700">Coming in Phase 5</p><h1 className="mt-2 text-3xl font-semibold">Your Veyra dashboard</h1><p className="mt-3 max-w-md text-slate-600">This route is ready. We will build the portfolio dashboard after authentication screens are complete.</p><Link to="/" className="mt-7 inline-flex rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white">Back to home</Link></div></main>
}
