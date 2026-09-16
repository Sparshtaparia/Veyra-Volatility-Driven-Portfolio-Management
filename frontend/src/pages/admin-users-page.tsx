import { Panel, PanelHeader, Badge } from "@/components/ui/primitives"

const demoUsers = [
  { name: "Sparsh T.", email: "sparsh@example.com", portfolios: 1, evaluations: 24, status: "ACTIVE" },
  { name: "Aarav M.", email: "aarav@example.com", portfolios: 2, evaluations: 61, status: "ACTIVE" },
  { name: "Ishita R.", email: "ishita@example.com", portfolios: 1, evaluations: 9, status: "ACTIVE" },
  { name: "Dev K.", email: "dev@example.com", portfolios: 1, evaluations: 3, status: "PENDING" },
]

export function AdminUsersPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-sm font-semibold text-slate-500">ADMIN</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Users</h1>
      </header>
      <Panel className="mt-6">
        <PanelHeader title="Users" subtitle="Shown with representative demo data until the admin analytics service is wired up." />
        <div className="overflow-x-auto px-6 py-4">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="pb-3 pr-4 font-semibold">User</th><th className="pb-3 pr-4 font-semibold">Portfolios</th><th className="pb-3 pr-4 font-semibold">Evaluations</th><th className="pb-3 font-semibold">Status</th></tr>
            </thead>
            <tbody>
              {demoUsers.map((user) => (
                <tr key={user.email} className="border-b border-slate-100 last:border-0">
                  <td className="py-3.5 pr-4"><p className="font-semibold text-slate-900">{user.name}</p><p className="text-xs text-slate-500">{user.email}</p></td>
                  <td className="py-3.5 pr-4 tabular-nums">{user.portfolios}</td>
                  <td className="py-3.5 pr-4 tabular-nums">{user.evaluations}</td>
                  <td className="py-3.5"><Badge tone={user.status === "ACTIVE" ? "emerald" : "amber"}>{user.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}