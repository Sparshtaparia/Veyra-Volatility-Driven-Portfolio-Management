import { useEffect, useState } from "react"
import { BarChart2, Brain, CheckCircle2, RefreshCw, Zap, ReceiptText, SlidersHorizontal, PackageCheck } from "lucide-react"

const PIPELINE_STEPS = [
  {
    icon: BarChart2,
    label: "Retrieving threshold",
    detail: "Fetching adaptive threshold and previous evaluation signals.",
    color: "text-sky-500",
    bg: "bg-sky-50",
    border: "border-sky-200",
  },
  {
    icon: Brain,
    label: "Calculating objective function",
    detail: "Solving for the portfolio that minimizes risk while achieving constraints.",
    color: "text-violet-500",
    bg: "bg-violet-50",
    border: "border-violet-200",
  },
  {
    icon: SlidersHorizontal,
    label: "Optimizing weights",
    detail: "Balancing volatility exposure against concentration risk.",
    color: "text-indigo-500",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
  },
  {
    icon: Zap,
    label: "Simulating execution",
    detail: "Generating BUY and SELL orders matching target weights.",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  {
    icon: ReceiptText,
    label: "Estimating impact",
    detail: "Applying bid-ask spread and transaction cost models.",
    color: "text-amber-500",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  {
    icon: PackageCheck,
    label: "Compiling paper trades",
    detail: "Finalizing paper rebalance simulation for review.",
    color: "text-slate-700",
    bg: "bg-slate-50",
    border: "border-slate-200",
  },
]

// How many ms to spend per step
const STEP_MS = 800

interface RebalancePipelineProps {
  running: boolean
  onComplete?: () => void
}

export function RebalancePipeline({ running, onComplete }: RebalancePipelineProps) {
  const [activeStep, setActiveStep] = useState(-1)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])

  useEffect(() => {
    if (!running) {
      setActiveStep(-1)
      setCompletedSteps([])
      return
    }

    setActiveStep(0)
    setCompletedSteps([])

    const timers: ReturnType<typeof setTimeout>[] = []

    PIPELINE_STEPS.forEach((_, i) => {
      timers.push(
        setTimeout(() => {
          setCompletedSteps((prev) => [...prev, i])
          if (i + 1 < PIPELINE_STEPS.length) {
            setActiveStep(i + 1)
          } else if (onComplete) {
            setTimeout(onComplete, 800)
          }
        }, STEP_MS * (i + 1))
      )
    })

    return () => timers.forEach(clearTimeout)
  }, [running, onComplete])

  if (!running) return null

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
        <RefreshCw className="size-5 animate-spin text-emerald-600" />
        <h2 className="text-lg font-bold text-slate-900">Simulating Rebalance…</h2>
      </div>

      <div className="mt-6 space-y-3">
        {PIPELINE_STEPS.map((step, i) => {
          const isActive = activeStep === i
          const isComplete = completedSteps.includes(i)
          const isPending = !isActive && !isComplete

          return (
            <div
              key={i}
              className={`flex items-start gap-4 rounded-xl border p-4 transition-all duration-500 ${
                isActive ? `bg-white shadow-sm ${step.border}` :
                isComplete ? "border-emerald-100 bg-emerald-50/50" :
                "border-transparent opacity-40 grayscale"
              }`}
            >
              <div
                className={`grid size-10 shrink-0 place-items-center rounded-full transition-colors duration-500 ${
                  isActive ? step.bg :
                  isComplete ? "bg-emerald-100 text-emerald-600" :
                  "bg-slate-100 text-slate-400"
                }`}
              >
                {isComplete ? (
                  <CheckCircle2 className="size-5" />
                ) : (
                  <step.icon className={`size-5 ${isActive ? step.color : ""}`} />
                )}
              </div>

              <div className="flex-1">
                <p
                  className={`text-sm font-bold transition-colors duration-500 ${
                    isActive ? "text-slate-900" :
                    isComplete ? "text-emerald-900" :
                    "text-slate-500"
                  }`}
                >
                  {step.label}
                </p>
                <p
                  className={`mt-0.5 text-xs transition-colors duration-500 ${
                    isActive ? "text-slate-500" :
                    isComplete ? "text-emerald-700/70" :
                    "text-slate-400"
                  }`}
                >
                  {step.detail}
                </p>
              </div>

              {isActive && (
                <div className="flex items-center gap-1.5 self-center pr-2">
                  <span className="size-1.5 animate-bounce rounded-full bg-emerald-500 [animation-delay:-0.3s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-emerald-500 [animation-delay:-0.15s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-emerald-500" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
