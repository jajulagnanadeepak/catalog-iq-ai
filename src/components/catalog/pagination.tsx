import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;

  return (
    <nav className="flex items-center justify-center gap-2 pt-8" aria-label="Pagination">
      <Button
        variant="outline"
        size="icon"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft className="size-4" />
      </Button>

      {Array.from({ length: pages }).map((_, i) => (
        <Button
          key={i}
          variant={page === i + 1 ? "default" : "outline"}
          size="icon"
          className={cn("w-9", page === i + 1 && "shadow-elevated")}
          onClick={() => onChange(i + 1)}
        >
          {i + 1}
        </Button>
      ))}

      <Button
        variant="outline"
        size="icon"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight className="size-4" />
      </Button>
    </nav>
  );
}
