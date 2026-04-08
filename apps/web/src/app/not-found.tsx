import Link from "next/link";
import { Home, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-6">
        <span className="text-2xl font-semibold text-muted-foreground font-mono">404</span>
      </div>
      <h1 className="text-2xl font-semibold text-foreground mb-2">Page not found</h1>
      <p className="text-muted-foreground mb-6 max-w-md">
        The page you are looking for does not exist or may have been moved.
      </p>
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/" />}>
          <Home className="h-4 w-4 mr-1.5" />Home
        </Button>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />Matches
        </Button>
      </div>
    </div>
  );
}
