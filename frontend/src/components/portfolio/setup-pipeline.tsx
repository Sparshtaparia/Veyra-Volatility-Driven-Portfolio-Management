import { useEffect, useState } from "react"
import { CheckCircle2, RefreshCw, FolderOpen, Database, Link as LinkIcon, Cpu } from "lucide-react"

const PIPELINE_STEPS = [
  {
    icon: FolderOpen,
    label: "Provisioning workspace",
    detail: "Allocating isolated portfolio environment and securing permissions.",
    color: "text-sky-500",
    bg: "bg-sky-50",
    border: "border-sky-200",
  },
  {
    icon: Database,
    label: "Ingesting holdings",
    detail: "Parsing securities, quantities, and average price data.",
    color: "text-violet-500",
    bg: "bg-violet-50",
    border: "border-violet-200",
  },
  {
    icon: LinkIcon,
    label: "Linking market data feeds",
    detail: "Establishing connection to live pricing APIs for Indian stocks.",
    color: "text-amber-500",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  {
    icon: Cpu,
    label: "Initializing volatility engine",
    detail: "Bootstrapping GARCH baseline and adaptive thresholds.",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
]

const STEP_MS = 1000

interface SetupPipelineProps {
  onComplete: () => void
}

export function SetupPipeline({ onComplete }: SetupPipelineProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])

  useEffect(() => {
    setActiveStep(0)
    setCompletedSteps([])

    const timers: ReturnType<typeof setTimeout>[] = []

    PIPELINE_STEPS.forEach((_, i) => {
      timers.push(
        setTimeout(() => {
          setCompletedSteps((prev) => [...prev, i])
          if (i + 1 < PIPELINE_STEPS.length) {
            setActiveStep(i + 1)
          } else {
            // Give a slight delay after the last step finishes before calling onComplete
            setTimeout(onComplete, 800)
          }
        }, STEP_MS * (i + 1))
      )
    })

    return () => timers.forEach(clearTimeout)
  }, [onComplete])

  return (
    <div className="mx-auto max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
        <RefreshCw className="size-5 animate-spin text-emerald-600" />
        <h2 className="text-lg font-bold text-slate-900">Setting up your portfolio…</h2>
      </div>

      <div className="mt-6 space-y-3">
        {PIPELINE_STEPS.map((step, i) => {
          const isActive = activeStep === i
          const isComplete = completedSteps.includes(i)

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

              <div className="flex-1 text-left">
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
