import { Link, useNavigate } from "@tanstack/react-router";
import { Camera, ChevronDown, LineChart, LogOut, Menu, User, Wallet } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { Logo, ThemeToggle } from "@/components/layout/brand";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth, getUserInitials } from "@/components/auth-context";
import { CartSheet } from "@/components/cart/cart-sheet";

const primaryLinks = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Search", to: "/search" },
  { label: "Copilot", to: "/copilot" },
  { label: "Stylist", to: "/stylist" },
] as const;

const exploreFeatures = [
  {
    label: "Budget Optimizer",
    to: "/budget",
    description: "Smart spending limits & cart allocation",
    icon: Wallet,
  },
  {
    label: "Visual Search",
    to: "/visual-search",
    description: "Find products from inspiration photos",
    icon: Camera,
  },
  {
    label: "Seasonal Recommendations",
    to: "/seasonal",
    description: "Catalog velocity & seasonal trend radar",
    icon: LineChart,
  },
] as const;

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    toast.success("Signed out successfully");
    navigate({ to: "/login" });
  };

  const initials = getUserInitials(user);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/70 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6">
        <Logo />

        {/* Desktop Navigation */}
        <nav className="hidden items-center gap-1 md:flex" aria-label="Main Navigation">
          {primaryLinks.map((link) => (
            <Link
              key={link.label}
              to={link.to}
              activeProps={{
                className: "bg-accent/70 text-foreground font-semibold",
              }}
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {link.label}
            </Link>
          ))}

          {/* Explore Dropdown for Extended Intelligence Tools */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="group inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Explore more features"
              >
                <span>Explore</span>
                <ChevronDown className="size-3.5 transition-transform duration-200 group-data-[state=open]:rotate-180" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-72 rounded-xl border border-border/80 bg-popover/95 p-1.5 shadow-elevated backdrop-blur-md"
            >
              {exploreFeatures.map((feat) => (
                <DropdownMenuItem
                  key={feat.label}
                  asChild
                  className="cursor-pointer rounded-lg p-2 focus:bg-accent"
                >
                  <Link to={feat.to} className="flex items-start gap-3 w-full">
                    <div className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                      <feat.icon className="size-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-semibold text-foreground">{feat.label}</span>
                      <span className="text-[11px] text-muted-foreground leading-tight">
                        {feat.description}
                      </span>
                    </div>
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <CartSheet />

          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8 rounded-full p-0">
                  <Avatar className="size-8 cursor-pointer ring-1 ring-border">
                    <AvatarFallback className="bg-primary text-xs font-semibold text-primary-foreground">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 shadow-elevated">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none truncate">
                      {user?.full_name || "CatalogIQ User"}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground truncate">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/profile" className="flex items-center gap-2 cursor-pointer">
                    <User className="size-4" />
                    <span>Profile</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/dashboard" className="flex items-center gap-2 cursor-pointer">
                    <span>Dashboard</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleLogout}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="size-4 mr-2" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="hidden sm:inline-flex rounded-lg text-sm font-medium"
              >
                <Link to="/login">Log in</Link>
              </Button>
              <Button
                asChild
                size="sm"
                className="hidden sm:inline-flex rounded-lg px-4 text-sm font-medium shadow-sm"
              >
                <Link to="/signup">Start free</Link>
              </Button>
            </>
          )}

          {/* Mobile Navigation Drawer */}
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-9 rounded-lg md:hidden"
                aria-label="Open navigation menu"
              >
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-80 p-6">
              <SheetTitle className="text-base font-semibold tracking-tight">Navigation</SheetTitle>
              <div className="mt-6 flex flex-col gap-1">
                {primaryLinks.map((link) => (
                  <Link
                    key={link.label}
                    to={link.to}
                    activeProps={{
                      className: "bg-accent text-foreground font-semibold",
                    }}
                    className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                  >
                    {link.label}
                  </Link>
                ))}

                <div className="my-2 border-t border-border/60 pt-2">
                  <span className="px-3 text-[11px] font-semibold text-muted-foreground tracking-wider uppercase">
                    Catalog Intelligence
                  </span>
                </div>

                {exploreFeatures.map((feat) => (
                  <Link
                    key={feat.label}
                    to={feat.to}
                    activeProps={{
                      className: "bg-accent text-foreground font-semibold",
                    }}
                    className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                  >
                    <feat.icon className="size-4 text-primary" />
                    <span>{feat.label}</span>
                  </Link>
                ))}

                <div className="mt-6 flex flex-col gap-2.5 border-t border-border/60 pt-6">
                  {isAuthenticated ? (
                    <>
                      <div className="flex items-center gap-3 px-3 py-2">
                        <Avatar className="size-8">
                          <AvatarFallback className="bg-primary text-xs font-semibold text-primary-foreground">
                            {initials}
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">
                            {user?.full_name || "CatalogIQ User"}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                        </div>
                      </div>
                      <Button
                        asChild
                        variant="outline"
                        className="w-full justify-center rounded-lg"
                      >
                        <Link to="/profile">Profile</Link>
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={handleLogout}
                        className="w-full justify-center rounded-lg text-destructive"
                      >
                        <LogOut className="size-4 mr-2" />
                        Log out
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        asChild
                        variant="outline"
                        className="w-full justify-center rounded-lg"
                      >
                        <Link to="/login">Log in</Link>
                      </Button>
                      <Button asChild className="w-full justify-center rounded-lg">
                        <Link to="/signup">Start free</Link>
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
