import { Sparkles } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Recommendation } from "@/lib/api/types";

export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const { product, title, reason, confidence } = recommendation;
  return (
    <Card className="flex gap-4 p-4 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-elevated">
      <Link
        to="/product/$productId"
        params={{ productId: product.id }}
        className="size-20 shrink-0 overflow-hidden rounded-lg bg-muted"
      >
        <img src={product.image} alt={product.name} loading="lazy" className="size-full object-cover" />
      </Link>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
          <Sparkles className="size-3.5" />
          {title}
        </div>
        <Link
          to="/product/$productId"
          params={{ productId: product.id }}
          className="mt-1 line-clamp-1 block font-medium hover:underline"
        >
          {product.name}
        </Link>
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{reason}</p>
        <div className="mt-2 flex items-center gap-3">
          <Progress value={confidence * 100} className="h-1.5" />
          <span className="shrink-0 text-xs text-muted-foreground">
            {Math.round(confidence * 100)}%
          </span>
          <span className="shrink-0 text-sm font-semibold">${product.price}</span>
        </div>
      </div>
    </Card>
  );
}
