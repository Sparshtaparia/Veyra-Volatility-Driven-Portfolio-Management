import { useEffect, useRef } from "react"
import { portfolioApi } from "@/api/portfolios"

const SEED_KEY = "veyra-demo-portfolio-id"
const SEEDED_FLAG = "veyra-demo-seeded-v1"

// Pre-canned holdings matching the Veyra reference UI screenshots
const DEMO_HOLDINGS = [
  { ticker: "TCS",      quantity: 20, average_price: 3200, current_price: 3482.5  },
  { ticker: "INFY",     quantity: 15, average_price: 1480, current_price: 1624.3  },
  { ticker: "HDFC",     quantity: 10, average_price: 1620, current_price: 1815.2  },
  { ticker: "RELIANCE", quantity: 8,  average_price: 2350, current_price: 2540.0  },
]

/**
 * Runs once per demo user session.
 * If no portfolio exists in localStorage, creates a portfolio + adds 4 demo holdings
 * via the real backend API. Safe to call multiple times — idempotent via the SEEDED_FLAG.
 */
export function useDemoSeed(isDemoUser: boolean) {
  const started = useRef(false)

  useEffect(() => {
    if (!isDemoUser) return
    if (started.current) return
    if (localStorage.getItem(SEEDED_FLAG)) return // already seeded this browser

    started.current = true

    async function seed() {
      try {
        // 1. Create portfolio
        const portfolio = await portfolioApi.create({
          name: "My Long-term Portfolio",
          currency: "INR",
        })
        const pid = portfolio.portfolio_id
        localStorage.setItem(SEED_KEY, pid)

        // 2. Add holdings in sequence
        for (const h of DEMO_HOLDINGS) {
          await portfolioApi.addHolding(pid, h)
        }

        // 3. Mark as seeded so we don't repeat on refresh
        localStorage.setItem(SEEDED_FLAG, "1")

        // 4. Force a full page reload so TanStack Query picks up the new portfolioId
        window.location.reload()
      } catch (err) {
        // Backend may not be running — silently ignore, page still works
        console.warn("[Veyra demo seed] Could not seed data:", err)
        localStorage.setItem(SEEDED_FLAG, "1") // don't retry on every mount
      }
    }

    seed()
  }, [isDemoUser])
}
