import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Bell, Loader2, LogIn, Shield, User } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth, getUserInitials } from "@/components/auth-context";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Your Profile — CatalogIQ AI" },
      {
        name: "description",
        content: "Manage your CatalogIQ AI account, style preferences and notification settings.",
      },
      { property: "og:title", content: "Your Profile — CatalogIQ AI" },
      { property: "og:description", content: "Account and preference settings." },
    ],
  }),
  component: ProfilePage,
});

const PREFS = [
  ["Personalised recommendations", "Use browsing history to tune AI results."],
  ["Price drop alerts", "Notify me when saved items get cheaper."],
  ["Weekly seasonal digest", "A curated edit every Monday morning."],
] as const;

function ProfilePage() {
  const { user, isLoading, isAuthenticated, updateProfile } = useAuth();

  const [fullName, setFullName] = useState("");
  const [preferredSize, setPreferredSize] = useState("");
  const [styleKeywords, setStyleKeywords] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name ?? "");
      setPreferredSize(user.preferred_size ?? "M");
      setStyleKeywords(user.style_keywords ?? "minimal, modern, neutral");
    }
  }, [user]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!isAuthenticated) {
      toast.error("Please log in to update your profile.");
      return;
    }

    setSaving(true);
    try {
      await updateProfile({
        full_name: fullName,
        preferred_size: preferredSize,
        style_keywords: styleKeywords,
      });
      toast.success("Profile updated successfully");
    } catch {
      toast.error("Failed to update profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const initials = getUserInitials(user);

  return (
    <AppShell title="Profile" description="Account, preferences and AI personalisation">
      {isLoading ? (
        <Card className="flex items-center justify-center p-16 shadow-card">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading profile…</span>
        </Card>
      ) : !isAuthenticated ? (
        <Card className="flex flex-col items-center gap-4 p-12 text-center shadow-card">
          <User className="size-10 text-muted-foreground" />
          <div>
            <h2 className="text-lg font-semibold">Not logged in</h2>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Sign in to manage your personalized style preferences, sizes, and saved
              recommendations.
            </p>
          </div>
          <div className="flex gap-3">
            <Button asChild>
              <Link to="/login">
                <LogIn className="size-4" /> Log in
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/signup">Create account</Link>
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card className="gap-6 p-6 shadow-card">
            <div className="flex items-center gap-4">
              <Avatar className="size-14">
                <AvatarFallback className="bg-primary font-semibold text-primary-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold">
                  {user?.full_name || "CatalogIQ User"}
                </h2>
                <p className="truncate text-sm text-muted-foreground">{user?.email}</p>
              </div>
              <Badge variant="secondary" className="ml-auto shrink-0">
                Active
              </Badge>
            </div>

            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSave}>
              <div className="space-y-2">
                <Label htmlFor="name">Full name</Label>
                <Input
                  id="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your Name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={user?.email ?? ""}
                  disabled
                  className="bg-muted/50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="size">Preferred size</Label>
                <Input
                  id="size"
                  value={preferredSize}
                  onChange={(e) => setPreferredSize(e.target.value)}
                  placeholder="e.g. M, L, 32/34"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="style">Style keywords</Label>
                <Input
                  id="style"
                  value={styleKeywords}
                  onChange={(e) => setStyleKeywords(e.target.value)}
                  placeholder="e.g. minimal, utility, neutral"
                />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={saving}>
                  {saving ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <User className="size-4" />
                  )}
                  {saving ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </form>
          </Card>

          <div className="space-y-6">
            <Card className="gap-4 p-6 shadow-card">
              <div className="flex items-center gap-2">
                <Bell className="size-4 text-primary" />
                <h2 className="text-sm font-semibold">AI &amp; notifications</h2>
              </div>
              {PREFS.map(([title, body]) => (
                <div key={title} className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium">{title}</p>
                    <p className="text-xs text-muted-foreground">{body}</p>
                  </div>
                  <Switch
                    defaultChecked
                    onCheckedChange={() => toast.success("Preference saved")}
                  />
                </div>
              ))}
            </Card>

            <Card className="gap-3 p-6 shadow-card">
              <div className="flex items-center gap-2">
                <Shield className="size-4 text-primary" />
                <h2 className="text-sm font-semibold">Account security</h2>
              </div>
              <p className="text-sm text-muted-foreground">
                Your workspace is secured with JWT authentication and encrypted sessions.
              </p>
              <Button variant="outline" onClick={() => toast.info("Password reset link requested")}>
                Reset password
              </Button>
            </Card>
          </div>
        </div>
      )}
    </AppShell>
  );
}
