import { createFileRoute } from "@tanstack/react-router";
import { toast } from "sonner";
import { Bell, Shield, User } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

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
  return (
    <AppShell title="Profile" description="Account, preferences and AI personalisation">
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="gap-6 p-6 shadow-card">
          <div className="flex items-center gap-4">
            <Avatar className="size-14">
              <AvatarFallback className="bg-primary text-primary-foreground">AR</AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-lg font-semibold">Ada Rivers</h2>
              <p className="text-sm text-muted-foreground">ada@catalogiq.ai</p>
            </div>
            <Badge variant="secondary" className="ml-auto">
              Pro plan
            </Badge>
          </div>

          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              toast.success("Profile updated");
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input id="name" defaultValue="Ada Rivers" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue="ada@catalogiq.ai" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="size">Preferred size</Label>
              <Input id="size" defaultValue="M" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="style">Style keywords</Label>
              <Input id="style" defaultValue="minimal, utility, neutral" />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit">
                <User className="size-4" /> Save changes
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
                <Switch defaultChecked onCheckedChange={() => toast.success("Preference saved")} />
              </div>
            ))}
          </Card>

          <Card className="gap-3 p-6 shadow-card">
            <div className="flex items-center gap-2">
              <Shield className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">Security</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Two-factor authentication is enabled for this workspace.
            </p>
            <Button variant="outline" onClick={() => toast.info("Password reset email sent")}>
              Reset password
            </Button>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
