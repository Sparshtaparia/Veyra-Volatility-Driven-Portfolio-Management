import { useState } from "react"
import { Activity, BellRing, BriefcaseBusiness, ChartLine, Gauge, House, LogOut, Menu, Settings, X } from "lucide-react"
import { Navigate, Link, NavLink, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "@/auth/auth-context"
import { getSavedPortfolioId } from "@/hooks/use-portfolio"
import { cn } from "cn"

const navItems = [
  { to: "/app", label: "Home", icon: House, end: true },
  { to: "/app/portfolio", label: "Portfolio", icon: BriefcaseBusiness },
  { to: "/app/evaluation", label: "Evaluation", icon: Gauge },
  { to: "/app/triggers", label: "Triggers", icon: BellRing },
  { to: "/app/activity", label: "Activity", icon: Activity },
  { to: "/app/analytics", label: "Analytics", icon: ChartLine },
  { to: "/app/settings", label: "Settings", icon: Settings },
]

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  cn(
    "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
    isActive ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
  )

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, signOut } = useAuth()
  const location = useLocation()
  return (
    <div className="flex h-full flex-col">
      <Link to="/app" className="flex items-center gap-2 px-2 py-5" onClick={onNavigate}>
        <img src="/logo.png" alt="Veyra Logo" className="size-9" />
        <span className="text-xl font-semibold tracking-tight text-slate-950">Veyra</span>
      </Link>
      <nav className="flex-1 space-y-1 px-2" aria-label="App navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={linkClasses}
            onClick={onNavigate}
          >
            <item.icon className="size-4.5 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-200 p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-800">
            {(user?.name ?? "U").slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{user?.name}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={() => signOut()}
          className="mt-1 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
        >
          <LogOut className="size-4" /> Sign out
        </button>
      </div>
      <span className="sr-only">{location.pathname}</span>
    </div>
  )
}

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const portfolioId = getSavedPortfolioId()

  if (!portfolioId) {
    return <Navigate to="/onboarding" replace />
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <SidebarContent />
      </aside>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/40" onClick={() => setMenuOpen(false)} aria-label="Close menu" />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white">
            <button onClick={() => setMenuOpen(false)} className="absolute right-3 top-4 grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100">
              <X className="size-5" />
            </button>
            <SidebarContent onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden">
          <Link to="/app" className="flex items-center gap-2">
            <img src="/logo.png" alt="Veyra Logo" className="size-8" />
            <span className="text-lg font-semibold tracking-tight">Veyra</span>
          </Link>
          <button onClick={() => setMenuOpen(true)} className="grid size-9 place-items-center rounded-lg border border-slate-200 text-slate-700" aria-label="Open menu">
            <Menu className="size-5" />
          </button>
        </header>
        <main className="px-4 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}