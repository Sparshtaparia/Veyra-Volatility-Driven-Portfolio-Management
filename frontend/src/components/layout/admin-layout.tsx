import { useState } from "react"
import { Activity, FileClock, LayoutGrid, LogOut, Menu, Settings2, UserCircle2, Users, X } from "lucide-react"
import { Link, NavLink, Outlet } from "react-router-dom"
import { useAuth } from "@/auth/auth-model"
import { cn } from "cn"

const navItems = [
  { to: "/admin", label: "Dashboard", icon: LayoutGrid, end: true },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/evaluations", label: "Evaluations", icon: Activity },
  { to: "/admin/system", label: "System", icon: Settings2 },
  { to: "/admin/audit", label: "Audit Logs", icon: FileClock },
]

export function AdminLayout() {
  const { signOut } = useAuth()
  const [open, setOpen] = useState(false)

  const sidebar = (
    <div className="flex h-full flex-col">
      <Link to="/admin" className="flex items-center gap-2 px-2 py-5">
        <span className="grid size-9 place-items-center rounded-lg bg-slate-950 text-sm font-bold text-white">V</span>
        <span>
          <span className="block text-xl font-semibold tracking-tight text-slate-950">Veyra</span>
          <span className="block text-xs font-medium uppercase tracking-wider text-slate-400">Admin</span>
        </span>
      </Link>
      <nav className="flex-1 space-y-1 px-2">
        <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Admin</p>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              cn("group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors", isActive ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950")
            }
          >
            <item.icon className="size-4.5 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-200 p-3">
        <Link to="/app" className="mb-2 flex items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950">
          <UserCircle2 className="size-4.5" /> Investor view
        </Link>
        <button onClick={() => signOut()} className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950">
          <LogOut className="size-4" /> Sign out
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/40" onClick={() => setOpen(false)} aria-label="Close menu" />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white">
            <button onClick={() => setOpen(false)} className="absolute right-3 top-4 grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100"><X className="size-5" /></button>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden">
          <span className="text-sm font-semibold uppercase tracking-wider text-slate-500">Admin</span>
          <button onClick={() => setOpen(true)} className="grid size-9 place-items-center rounded-lg border border-slate-200 text-slate-700" aria-label="Open menu"><Menu className="size-5" /></button>
        </header>
        <main className="px-4 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
