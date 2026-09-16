import {
  Activity,
  BarChart2,
  Bell,
  BriefcaseBusiness,
  ChevronDown,
  ClipboardList,
  Home,
  Search,
  Settings,
  TrendingUp,
  Zap,
} from "lucide-react"
import { NavLink, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/auth-context"

const navigation = [
  { label: "Home",       icon: Home,              to: "/app",              end: true  },
  { label: "Portfolio",  icon: BriefcaseBusiness, to: "/app/portfolio",    end: false },
  { label: "Evaluation", icon: ClipboardList,     to: "/app/evaluation",  end: false },
  { label: "Analytics",  icon: BarChart2,         to: "/app/analytics",   end: false },
  { label: "Triggers",   icon: Zap,               to: "/app/rebalance",   end: false },
  { label: "Activity",   icon: Activity,          to: "/app/activity",    end: false },
  { label: "Settings",   icon: Settings,          to: "/app/settings",    end: false },
]

function getInitials(name: string, email: string): string {
  if (name && name !== "Demo Investor" && name !== "Veyra Admin") {
    return name.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase()
  }
  const prefix = email.split("@")[0]
  const parts = prefix.split(/[._-]/)
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "U"
}

function getDisplayName(name: string, email: string): string {
  if (name && name !== "Demo Investor") return name
  const prefix = email.split("@")[0]
  return prefix.split(/[._-]/).map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" ")
}

function useContextualCard(path: string) {
  if (path.startsWith("/app/analytics")) return { icon: <BarChart2 className="size-4 text-emerald-700" />, heading: "Data-driven insights.", sub: "Better decisions with Veyra.", cta: "Upgrade →" }
  if (path.startsWith("/app/settings")) return { icon: <TrendingUp className="size-4 text-emerald-700" />, heading: "Invest smarter every day.", sub: "Unlock advanced insights.", cta: "Learn More →" }
  return { icon: <span className="grid size-5 place-items-center rounded bg-[#14532d] text-[9px] font-bold text-white">V</span>, heading: "Disciplined today.", sub: "A more resilient tomorrow.", cta: null }
}

export function InvestorShell({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const card = useContextualCard(pathname)
  const initials = user ? getInitials(user.name, user.email) : "U"
  const displayName = user ? getDisplayName(user.name, user.email) : "Investor"

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f6f7]">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="hidden w-[220px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
        {/* Logo */}
        <div className="px-5 pb-4 pt-5">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-md bg-[#14532d] text-sm font-bold text-white">
              V
            </span>
            <div>
              <p className="text-sm font-bold leading-none tracking-tight text-slate-900">Veyra</p>
              <p className="mt-0.5 text-[10px] leading-tight text-slate-500">
                Smarter Portfolios<br />for a Volatile World.
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 px-3 py-2" aria-label="Investor navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.to + item.label}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={`size-4 shrink-0 ${isActive ? "text-emerald-700" : "text-slate-500"}`}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Contextual sidebar card */}
        <div className="p-3">
          <div className="rounded-xl bg-emerald-50 p-4">
            <div className="flex items-center gap-2">
              {card.icon}
              <p className="text-xs font-semibold text-emerald-900">{card.heading}</p>
            </div>
            <p className="mt-1.5 text-xs leading-4 text-slate-600">{card.sub}</p>
            {card.cta && (
              <button className="mt-2.5 text-xs font-semibold text-emerald-700 hover:underline">
                {card.cta}
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-5">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 lg:hidden">
            <span className="grid size-7 place-items-center rounded-md bg-[#14532d] text-xs font-bold text-white">
              V
            </span>
            <span className="text-sm font-bold">Veyra</span>
          </div>

          {/* Search */}
          <div className="relative hidden max-w-xs flex-1 lg:block">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search assets, insights, or help..."
              className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-50 transition"
            />
          </div>

          <div className="ml-auto flex items-center gap-3">
            {/* Bell */}
            <button className="relative grid size-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 transition">
              <Bell className="size-4" />
              <span className="absolute right-2 top-2 size-1.5 rounded-full bg-rose-500" />
            </button>

            {/* User */}
            <button
              onClick={signOut}
              title="Click to sign out"
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100 transition"
            >
              <span className="grid size-8 place-items-center rounded-full bg-emerald-600 text-xs font-bold text-white">
                {initials}
              </span>
              <span className="hidden text-sm font-medium text-slate-800 sm:block">
                {displayName}
              </span>
              <ChevronDown className="size-3.5 text-slate-400" />
            </button>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          {/* Mobile bottom nav */}
          <nav className="fixed bottom-0 left-0 right-0 z-20 flex border-t border-slate-200 bg-white lg:hidden">
            {navigation.slice(0, 5).map((item) => (
              <NavLink
                key={item.to + item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition ${
                    isActive ? "text-emerald-700" : "text-slate-500"
                  }`
                }
              >
                <item.icon className="size-5" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="pb-16 lg:pb-0">{children}</div>
        </main>
      </div>
    </div>
  )
}
