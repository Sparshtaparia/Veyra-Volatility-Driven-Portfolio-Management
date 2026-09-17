import { useEffect, useState } from "react"
import { Activity, BarChart2, Brain, CheckCircle2, RefreshCw, ShieldCheck, TrendingUp, Zap } from "lucide-react"

const PIPELINE_STEPS = [
  {
    icon: BarChart2,
    label: "Fetching market data",
    detail: "Pulling 550 days of OHLCV history for your holdings via yfinance",
    color: "text-sky-500",
    bg: "bg-sky-50",
    border: "border-sky-200",
  },
  {
    icon: Activity,
    label: "Running GARCH volatility model",
    detail: "Fitting GARCH(1,1) to estimate conditional volatility per asset",
    color: "text-violet-500",
    bg: "bg-violet-50",
    border: "border-violet-200",
  },
  {
    icon: TrendingUp,
    label: "Detecting market regime",
    detail: "Classifying market stress level: LOW / MEDIUM / HIGH / CRISIS",
    color: "text-amber-500",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  {
    icon: Zap,
    label: "Computing factor signals",
    detail: "RSI · ATR · MACD · Bollinger Width · Fama-French 5-factor exposures",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  {
    icon: ShieldCheck,
    label: "Assessing signal reliability",
    detail: "Scoring each signal against model R², volatility ratios and past accuracy",
    color: "text-rose-500",
    bg: "bg-rose-50",
    border: "border-rose-200",
  },
  {
    icon: Brain,
    label: "Applying state-coupled operator",
    detail: "Attenuating signals based on risk state, reliability and regime",
    color: "text-indigo-500",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
  },
  {
    icon: RefreshCw,
    label: "Generating Veyra decision",
    detail: "Computing composite risk, allocation targets and final HOLD / ADAPT verdict",
    color: "text-slate-700",
    bg: "bg-slate-50",
    border: "border-slate-200",
  },
]

// How many ms to spend per step (total ~9s leaving headroom for real API)
const STEP_MS = 1300

interface EvaluationPipelineProps {
  running: boolean
}

export function EvaluationPipeline({ running }: EvaluationPipelineProps) {
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
      // Mark step as complete after STEP_MS, advance to next
      timers.push(
        setTimeout(() => {
          setCompletedSteps((prev) => [...prev, i])
          if (i + 1 < PIPELINE_STEPS.length) {
            setActiveStep(i + 1)
          }
        }, STEP_MS * (i + 1))
      )
    })

    return () => timers.forEach(clearTimeout)
  }, [running])

  if (!running && activeStep === -1) return null

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-xl bg-emerald-100">
          <Brain className="size-5 text-emerald-700" />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-900">Veyra Intelligence Pipeline</p>
          <p className="text-xs text-slate-500">Running quantitative analysis on your portfolio…</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
          Live
        </div>
      </div>

      {/* Steps */}
      <ol className="space-y-2.5">
        {PIPELINE_STEPS.map((step, i) => {
          const isDone = completedSteps.includes(i)
          const isActive = activeStep === i
          const isPending = !isDone && !isActive
          const Icon = step.icon

          return (
            <li
              key={step.label}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 transition-all duration-500 ${
                isDone
                  ? "border-emerald-200 bg-emerald-50/60 opacity-80"
                  : isActive
                  ? `${step.border} ${step.bg} shadow-sm`
                  : "border-slate-100 bg-slate-50/50 opacity-40"
              }`}
            >
              {/* Icon / Spinner / Check */}
              <span
                className={`mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg transition-all ${
                  isDone
                    ? "bg-emerald-100"
                    : isActive
                    ? `${step.bg}`
                    : "bg-slate-100"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="size-4 text-emerald-600" />
                ) : isActive ? (
                  <Icon className={`size-4 ${step.color} animate-pulse`} />
                ) : (
                  <Icon className="size-4 text-slate-400" />
                )}
              </span>

              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm font-medium leading-tight ${
                    isDone ? "text-emerald-700" : isActive ? "text-slate-900" : "text-slate-400"
                  }`}
                >
                  {step.label}
                </p>
                {(isActive || isDone) && (
                  <p className={`mt-0.5 text-xs ${isDone ? "text-emerald-600/70" : "text-slate-500"}`}>
                    {step.detail}
                  </p>
                )}
              </div>

              {/* Progress bar for active step */}
              {isActive && (
                <div className="mt-1 h-1 w-24 shrink-0 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className={`h-full rounded-full ${step.color.replace("text-", "bg-")} animate-[progress_1.3s_ease-in-out_forwards]`}
                    style={{ animation: `progressBar ${STEP_MS}ms ease-in-out forwards` }}
                  />
                </div>
              )}

              {isDone && (
                <span className="mt-1 shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                  Done
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {/* Progress summary */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
          <span>{completedSteps.length} of {PIPELINE_STEPS.length} steps complete</span>
          <span>{Math.round((completedSteps.length / PIPELINE_STEPS.length) * 100)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${(completedSteps.length / PIPELINE_STEPS.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}
