/**
 * Reusable loading components for InsideEdge.
 */

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-8 ${className}`}>
      <div className="relative w-8 h-8">
        <div className="absolute inset-0 rounded-full border-2 border-border" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary animate-spin" />
      </div>
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-lg px-4 py-3 animate-pulse">
      <div className="h-3 w-16 bg-muted rounded mb-2" />
      <div className="h-7 w-20 bg-muted rounded" />
    </div>
  );
}

export function MatchCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-lg px-4 py-3 animate-pulse">
      <div className="h-4 w-64 bg-muted rounded mb-2" />
      <div className="h-3 w-48 bg-muted rounded" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-border">
        <div className="h-3 w-32 bg-muted rounded animate-pulse" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-2 flex justify-between animate-pulse">
          <div className="h-4 w-28 bg-muted rounded" />
          <div className="h-4 w-12 bg-muted rounded" />
        </div>
      ))}
    </div>
  );
}
