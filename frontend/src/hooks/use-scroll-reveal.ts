import { useEffect, useRef, useState } from "react"

export function useScrollReveal(options = { threshold: 0.1, triggerOnce: true }) {
  const ref = useRef<HTMLElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true)
        if (options.triggerOnce) {
          observer.unobserve(el)
        }
      } else if (!options.triggerOnce) {
        setInView(false)
      }
    }, options)

    observer.observe(el)
    return () => {
      if (el) observer.unobserve(el)
    }
  }, [options.threshold, options.triggerOnce])

  return { ref, inView }
}
