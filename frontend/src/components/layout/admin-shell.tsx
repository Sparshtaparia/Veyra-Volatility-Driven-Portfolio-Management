import { Activity, ClipboardList, LayoutDashboard, LogOut, ServerCog, Users } from "lucide-react"
import { NavLink } from "react-router-dom"
import { useAuth } from "@/auth/auth-model"

const navigation = [
  { label: "Overview", icon: LayoutDashboard, to: "/admin", end: true },
  { label: "Users", icon: Users, to: "/admin/users", end: false },
  { label: "Evaluations", icon: Activity, to: "/admin/evaluations", end: false },
  { label: "System", icon: ServerCog, to: "/admin/system", end: false },
  { label: "Audit logs", icon: ClipboardList, to: "/admin/audit", end: false },
]

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { signOut } = useAuth()

  return (
    <div className="min-h-screen bg-slate-100 text-slate-950 lg:grid lg:grid-cols-[248px_1fr]">
      {/* Desktop Sidebar */}
      <aside className="hidden bg-slate-950 px-4 py-6 text-white lg:flex lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-2.5 px-3">
            <span className="grid size-8 place-items-center rounded-lg bg-emerald-400 text-sm font-bold text-slate-950">
              V
            </span>
            <div>
              <span className="text-xl font-semibold tracking-tight">Veyra</span>
              <span className="ml-2 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Admin
              </span>
            </div>
          </div>

          <p className="mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Navigation
          </p>

          <nav className="mt-2.5 space-y-1" aria-label="Admin desktop navigation">
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                    isActive
                      ? "bg-white/15 text-white"
                      : "text-slate-400 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <item.icon className="size-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="border-t border-slate-800 pt-4">
          <button
            type="button"
            onClick={signOut}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-white/10 hover:text-white focus-visible:ring-2 focus-visible:ring-emerald-400"
          >
            <LogOut className="size-4 shrink-0" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="min-w-0 flex flex-col min-h-screen">
        {/* Mobile Header */}
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white px-4 py-3 shadow-2xs lg:hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="grid size-8 place-items-center rounded-lg bg-slate-950 text-sm font-bold text-white">
                V
              </span>
              <div>
                <span className="font-semibold text-slate-950">Veyra Admin</span>
                <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                  Console
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={signOut}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-950"
            >
              <LogOut className="size-3.5" />
              Sign out
            </button>
          </div>

          <nav
            className="mt-3 flex gap-1.5 overflow-x-auto pb-1 scrollbar-none"
            aria-label="Admin mobile navigation"
          >
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
                  }`
                }
              >
                <item.icon className="size-3.5 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </header>

        {/* Page Content */}
        <div className="flex-1">{children}</div>
      </div>
    </div>
  )
}
