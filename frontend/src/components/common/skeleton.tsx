// Reusable shimmer skeleton components for loading states.
// Usage:  <Skeleton className="h-6 w-48" />
//         <SkeletonCard lines={3} />

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%] ${className}`}
      style={{ animation: "shimmer 1.6s ease-in-out infinite", ...style }}
    />
  )
}

export function SkeletonText({ lines = 2, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={`h-4 ${i === lines - 1 ? "w-3/5" : "w-full"}`} />
      ))}
    </div>
  )
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3 ${className}`}>
      <div className="flex items-center gap-3">
        <Skeleton className="size-9 rounded-lg shrink-0" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-7 w-40" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
    </div>
  )
}

export function SkeletonStatCard() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm space-y-2">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-7 w-36" />
      <Skeleton className="h-3 w-20" />
    </div>
  )
}

export function SkeletonTable({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50 px-5 py-3.5 flex gap-4">
        {[24, 40, 60, 32, 32].map((w, i) => (
          <Skeleton key={i} className={`h-3 w-${w} shrink-0`} style={{ width: `${w * 4}px` }} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 border-b border-slate-100 last:border-0 px-5 py-4">
          <Skeleton className="size-8 rounded-full shrink-0" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-32 flex-1" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-12" />
        </div>
      ))}
    </div>
  )
}
