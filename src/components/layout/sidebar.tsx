import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Search,
  MessageSquareText,
  Shirt,
  Wallet,
  CalendarRange,
  ImageUp,
  UserRound,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/brand";

export const navItems = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Semantic Search", to: "/search", icon: Search },
  { label: "AI Copilot", to: "/copilot", icon: MessageSquareText },
  { label: "AI Stylist", to: "/stylist", icon: Shirt },
  { label: "Budget Optimizer", to: "/budget", icon: Wallet },
  { label: "Seasonal", to: "/seasonal", icon: CalendarRange },
  { label: "Visual Search", to: "/visual-search", icon: ImageUp },
  { label: "Profile", to: "/profile", icon: UserRound },
] as const;

export function Sidebar({
  collapsed,
  onToggle,
  onNavigate,
}: {
  collapsed?: boolean;
  onToggle?: () => void;
  onNavigate?: () => void;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-16 items-center justify-between px-3">
        <Logo compact={collapsed ?? false} />
        {onToggle && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="hidden lg:inline-flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
          </Button>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        {navItems.map((item) => {
          const active = pathname === item.to;
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              title={item.label}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                active
                  ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-elevated"
                  : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
            >
              <item.icon className="size-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="m-3 rounded-xl border border-sidebar-border surface-glow p-3">
          <p className="text-xs font-semibold">Model: catalog-embed v3</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Indexing 128k SKUs · latency 82ms p95
          </p>
        </div>
      )}
    </aside>
  );
}
