import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/budget")({
  component: BudgetPage,
});

function BudgetPage() {
  return null;
}
