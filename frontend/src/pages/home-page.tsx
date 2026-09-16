import { ArrowRight, MonitorCheck, RefreshCw, Scale, ShieldCheck, Waves } from "lucide-react"
import { Link } from "react-router-dom"
import { SiteHeader } from "@/components/layout/site-header"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"

export function HomePage() {
  const heroReveal = useScrollReveal()
  const worksReveal = useScrollReveal({ threshold: 0.2, triggerOnce: true })
  const whyReveal = useScrollReveal({ threshold: 0.2, triggerOnce: true })

  return (
    <div className="min-h-screen bg-[#f8faf9] text-slate-950 overflow-x-hidden">
      <SiteHeader />
      <main>
        {/* Hero Section */}
        <section 
          ref={heroReveal.ref as any}
          className={`relative overflow-hidden px-5 pb-16 pt-16 sm:px-8 sm:pb-24 sm:pt-24 transition-all duration-1000 ${
            heroReveal.inView ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"
          }`}
        >
          <div className="absolute inset-x-0 top-0 -z-0 h-96 bg-[radial-gradient(circle_at_65%_5%,#d1fae5,transparent_38%),radial-gradient(circle_at_10%_25%,#e0f2fe,transparent_32%)]" />
          <div className="relative mx-auto max-w-4xl text-center">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-800">
              <ShieldCheck className="size-4" /> Volatility-aware portfolio guidance
            </p>
            <h1 className="mx-auto max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl">
              Your portfolio doesn't need to be rebuilt every day.
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-slate-600">
              Veyra tells you when it needs to change — and what to do about it. Monitor, evaluate, adapt.
            </p>
            <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
              <Link to="/sign-up" className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-emerald-500 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400">
                Create Portfolio <ArrowRight className="size-4" />
              </Link>
              <Link to="/sign-in" className="inline-flex h-12 items-center justify-center rounded-lg border border-slate-300 bg-white px-6 text-sm font-semibold text-slate-800 transition hover:bg-slate-50">
                Sign In
              </Link>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section 
          id="how-it-works" 
          ref={worksReveal.ref as any}
          className="border-t border-slate-200 bg-white px-5 py-16 sm:px-8 sm:py-20"
        >
          <div className="mx-auto max-w-6xl">
            <div className={`transition-all duration-700 delay-100 ${worksReveal.inView ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`}>
              <p className="text-center text-sm font-semibold uppercase tracking-wider text-emerald-700">How it works</p>
              <h2 className="mt-2 text-center text-3xl font-semibold tracking-tight">Monitor → Evaluate → Adapt</h2>
            </div>
            
            <div className="mx-auto mt-12 max-w-2xl">
              <FlowStep 
                icon={<MonitorCheck className="size-5" />} 
                label="YOUR PORTFOLIO" 
                text="Veyra watches your holdings, their prices and how the market is moving." 
                accent="bg-emerald-500" 
                inView={worksReveal.inView} 
                delay="delay-[200ms]" 
              />
              <FlowArrow inView={worksReveal.inView} delay="delay-[300ms]" />
              <FlowStep 
                icon={<Waves className="size-5" />} 
                label="MARKET CONDITIONS" 
                text="Volatility regimes and price signals are read from the market — not from guesswork." 
                accent="bg-sky-500" 
                inView={worksReveal.inView} 
                delay="delay-[400ms]" 
              />
              <FlowArrow inView={worksReveal.inView} delay="delay-[500ms]" />
              <FlowStep 
                icon={<RefreshCw className="size-5" />} 
                label="VEYRA EVALUATION" 
                text="A risk-aware engine combines the market state, your portfolio and signal reliability." 
                accent="bg-indigo-500" 
                inView={worksReveal.inView} 
                delay="delay-[600ms]" 
              />
              <FlowArrow inView={worksReveal.inView} delay="delay-[700ms]" />
              <FlowStep 
                icon={<Scale className="size-5" />} 
                label="HOLD / ADAPT" 
                text="You get a clear answer: hold, or review the recommended change." 
                accent="bg-amber-500" 
                inView={worksReveal.inView} 
                delay="delay-[800ms]" 
              />
            </div>
          </div>
        </section>

        {/* Why Veyra Section */}
        <section 
          id="why-veyra" 
          ref={whyReveal.ref as any}
          className="px-5 py-16 sm:px-8 sm:py-20"
        >
          <div className="mx-auto max-w-6xl">
            <div className={`transition-all duration-700 delay-100 ${whyReveal.inView ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`}>
              <p className="text-center text-sm font-semibold uppercase tracking-wider text-emerald-700">Why Veyra</p>
              <h2 className="mt-2 text-center text-3xl font-semibold tracking-tight">Built for investors, powered by markets</h2>
            </div>
            
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <ValueCard 
                icon={<Waves className="size-5" />} 
                title="Volatility-aware" 
                text="Recognizes when markets get choppy and treats calm and chaotic periods differently." 
                inView={whyReveal.inView} 
                delay="delay-[200ms]" 
              />
              <ValueCard 
                icon={<ShieldCheck className="size-5" />} 
                title="Risk-aware" 
                text="Weighs concentration and exposure in every recommendation, not just raw returns." 
                inView={whyReveal.inView} 
                delay="delay-[300ms]" 
              />
              <ValueCard 
                icon={<RefreshCw className="size-5" />} 
                title="Adaptive" 
                text="Adjusts its own sensitivity over time so guidance stays relevant as conditions change." 
                inView={whyReveal.inView} 
                delay="delay-[400ms]" 
              />
              <ValueCard 
                icon={<MonitorCheck className="size-5" />} 
                title="Portfolio-focused" 
                text="Starts from the portfolio you actually hold and only tells you to act when needed." 
                inView={whyReveal.inView} 
                delay="delay-[500ms]" 
              />
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

function FlowStep({ icon, label, text, accent, inView, delay }: { icon: React.ReactNode; label: string; text: string; accent: string; inView: boolean; delay: string }) {
  return (
    <div className={`flex flex-col items-center gap-4 rounded-2xl border border-slate-200 bg-[#f8faf9] p-7 sm:flex-row sm:gap-6 transition-all duration-700 ${delay} ${inView ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`}>
      <span className={`grid size-12 shrink-0 place-items-center rounded-xl text-white ${accent}`}>{icon}</span>
      <div className="text-center sm:text-left">
        <p className="text-sm font-bold tracking-wide text-slate-900">{label}</p>
        <p className="mt-1 leading-6 text-slate-600">{text}</p>
      </div>
    </div>
  )
}

function FlowArrow({ inView, delay }: { inView: boolean; delay: string }) {
  return (
    <div className={`mx-auto -my-1 grid w-12 place-items-center py-2 transition-all duration-700 ${delay} ${inView ? "opacity-100 scale-100" : "opacity-0 scale-75"}`}>
      <ArrowRight className="size-6 rotate-90 text-slate-300" />
    </div>
  )
}

function ValueCard({ icon, title, text, inView, delay }: { icon: React.ReactNode; title: string; text: string; inView: boolean; delay: string }) {
  return (
    <article className={`rounded-xl border border-slate-200 bg-white p-6 transition-all duration-700 ${delay} ${inView ? "translate-y-0 opacity-100 shadow-sm" : "translate-y-12 opacity-0"} hover:shadow-lg hover:shadow-slate-200/60 hover:-translate-y-1`}>
      <span className="grid size-11 place-items-center rounded-lg bg-emerald-100 text-emerald-800">{icon}</span>
      <h3 className="mt-5 text-lg font-semibold">{title}</h3>
      <p className="mt-2 leading-6 text-slate-600">{text}</p>
    </article>
  )
}