import { useEffect, useRef, useState } from "react"

type ScrollRevealOptions = { threshold?: number; triggerOnce?: boolean }

export function useScrollReveal({
  threshold = 0.1,
  triggerOnce = true,
}: ScrollRevealOptions = {}) {
  const ref = useRef<HTMLElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true)
        if (triggerOnce) {
          observer.unobserve(el)
        }
      } else if (!triggerOnce) {
        setInView(false)
      }
    }, { threshold })

    observer.observe(el)
    return () => {
      if (el) observer.unobserve(el)
    }
  }, [threshold, triggerOnce])

  return [ref, inView] as const
}
