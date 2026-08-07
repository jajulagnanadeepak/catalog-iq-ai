import { Link } from "@tanstack/react-router";
import { Moon, Sun, Sparkle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2">
      <span className="grid size-8 place-items-center rounded-lg gradient-hero text-primary-foreground shadow-elevated">
        <Sparkle className="size-4" />
      </span>
      {!compact && (
        <span className="font-display text-lg font-semibold tracking-tight">
          Catalog<span className="text-gradient">IQ</span>
        </span>
      )}
    </Link>
  );
}

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle dark mode">
      {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
