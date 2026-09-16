import { AlertCircle, Code2, Lock } from "lucide-react"

interface SchemaField {
  name: string
  type: string
  description: string
}

interface UnavailableStateProps {
  title: string
  description: string
  badge?: string
  requiredEndpoint?: string
  expectedFields?: SchemaField[]
  notes?: string[]
  icon?: React.ReactNode
}

export function UnavailableState({
  title,
  description,
  badge = "Awaiting backend endpoint",
  requiredEndpoint,
  expectedFields,
  notes,
  icon,
}: UnavailableStateProps) {
  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-lg bg-slate-100 text-slate-700">
              {icon ?? <Lock className="size-5" />}
            </div>
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800 border border-amber-200">
                <AlertCircle className="size-3" />
                {badge}
              </span>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">{title}</h2>
            </div>
          </div>
        </div>

        <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          {description}
        </p>

        {requiredEndpoint && (
          <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Code2 className="size-3.5" />
              Required Backend Contract
            </div>
            <code className="mt-2 block font-mono text-sm font-medium text-slate-900">
              {requiredEndpoint}
            </code>
          </div>
        )}

        {expectedFields && expectedFields.length > 0 && (
          <div className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Expected API Schema Contract
            </h3>
            <div className="mt-2 overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-600">
                  <tr>
                    <th className="px-4 py-2.5">Field</th>
                    <th className="px-4 py-2.5">Type</th>
                    <th className="px-4 py-2.5">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {expectedFields.map((field) => (
                    <tr key={field.name}>
                      <td className="px-4 py-2.5 font-mono text-xs font-semibold text-slate-900">
                        {field.name}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                        {field.type}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600">
                        {field.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {notes && notes.length > 0 && (
          <div className="mt-6 rounded-lg bg-slate-50 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Architectural Constraints
            </h4>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs leading-5 text-slate-600">
              {notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
