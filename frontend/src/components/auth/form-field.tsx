import type { InputHTMLAttributes } from "react"

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }

export function FormField({ label, error, id, className = "", ...props }: FormFieldProps) {
  return <label className="block" htmlFor={id}><span className="text-sm font-medium text-slate-800">{label}</span><input id={id} className={`mt-2 h-12 w-full rounded-lg border bg-white px-3.5 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 ${error ? "border-red-400" : "border-slate-300"} ${className}`} {...props} />{error && <span className="mt-1.5 block text-sm text-red-600">{error}</span>}</label>
}
