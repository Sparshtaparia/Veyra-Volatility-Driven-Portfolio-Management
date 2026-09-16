export function currency(value: number, code = "INR") {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: code, maximumFractionDigits: 0 }).format(value)
}

export function percent(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`
}

export function signedPercent(value: number, digits = 1) {
  const prefix = value > 0 ? "+" : ""
  return `${prefix}${(value * 100).toFixed(digits)}%`
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value))
}

export function longDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" }).format(new Date(value))
}

export function shortDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short" }).format(new Date(value))
}