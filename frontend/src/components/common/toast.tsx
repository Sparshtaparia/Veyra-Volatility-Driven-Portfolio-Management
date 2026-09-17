/**
 * Ultra-lightweight toast notification system.
 * Usage:
 *   const { toast } = useToast()
 *   toast({ title: "Holding added!", type: "success" })
 *
 * Wrap your app root (or shell) with <Toaster /> once.
 */
import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, Info, XCircle, AlertTriangle, X } from "lucide-react"
import { ToastContext, type Toast, type ToastType } from "@/components/common/toast-context"

// ─── Provider ─────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback((opts: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2)
    const duration = opts.duration ?? 3500
    setToasts((prev) => [...prev, { id, ...opts }])
    setTimeout(() => dismiss(id), duration)
  }, [dismiss])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast stack — fixed top-right */}
      <div
        aria-live="polite"
        className="fixed right-4 top-4 z-[200] flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ─── Single toast item ────────────────────────────────────────────────────

const ICON: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 className="size-4 text-emerald-600 shrink-0" />,
  error:   <XCircle      className="size-4 text-rose-600 shrink-0" />,
  info:    <Info         className="size-4 text-blue-600 shrink-0" />,
  warning: <AlertTriangle className="size-4 text-amber-500 shrink-0" />,
}

const BORDER: Record<ToastType, string> = {
  success: "border-emerald-200",
  error:   "border-rose-200",
  info:    "border-blue-200",
  warning: "border-amber-200",
}

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [visible, setVisible] = useState(false)
  const type = t.type ?? "info"

  useEffect(() => {
    const r = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(r)
  }, [])

  return (
    <div
      className={`pointer-events-auto flex w-full items-start gap-3 rounded-xl border bg-white px-4 py-3.5 shadow-lg transition-all duration-300 ${
        BORDER[type]
      } ${visible ? "translate-y-0 opacity-100" : "-translate-y-2 opacity-0"}`}
    >
      <span className="mt-0.5">{ICON[type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-900 leading-tight">{t.title}</p>
        {t.description && (
          <p className="mt-0.5 text-xs text-slate-500">{t.description}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(t.id)}
        className="mt-0.5 shrink-0 rounded p-0.5 text-slate-400 hover:text-slate-700 transition"
      >
        <X className="size-3.5" />
      </button>
    </div>
  )
}
