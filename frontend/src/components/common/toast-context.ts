import { createContext, useContext } from "react"

export type ToastType = "success" | "error" | "info" | "warning"

export type Toast = {
  id: string
  title: string
  description?: string
  type?: ToastType
  duration?: number
}

export type ToastContextValue = {
  toast: (opts: Omit<Toast, "id">) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error("useToast must be used inside <ToastProvider>")
  return context
}
