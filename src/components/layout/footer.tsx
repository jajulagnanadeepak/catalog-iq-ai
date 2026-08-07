import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/layout/brand";

const columns = [
  {
    title: "Product",
    links: [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Semantic Search", to: "/search" },
      { label: "Visual Search", to: "/visual-search" },
    ],
  },
  {
    title: "AI Tools",
    links: [
      { label: "Shopping Copilot", to: "/copilot" },
      { label: "AI Stylist", to: "/stylist" },
      { label: "Budget Optimizer", to: "/budget" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Log in", to: "/login" },
      { label: "Sign up", to: "/signup" },
      { label: "Profile", to: "/profile" },
    ],
  },
] as const;

export function Footer() {
  return (
    <footer className="border-t border-border/60 bg-card/40">
      <div className="mx-auto grid w-full max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm text-muted-foreground">
            Retail intelligence for catalogs that think. Semantic discovery, styling and budget
            optimisation in one layer.
          </p>
        </div>
        {columns.map((col) => (
          <div key={col.title}>
            <h3 className="text-sm font-semibold">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.to}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border/60 py-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} CatalogIQ AI. All rights reserved.
      </div>
    </footer>
  );
}
