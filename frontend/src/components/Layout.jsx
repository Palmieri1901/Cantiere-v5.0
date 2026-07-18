import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LayoutDashboard, Users, Grid3x3, Settings2, Sailboat } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard" },
  { to: "/clienti", label: "Clienti", icon: Users, testId: "nav-clienti" },
  { to: "/posti-barca", label: "Posti Barca", icon: Grid3x3, testId: "nav-posti-barca" },
  { to: "/tariffe", label: "Tariffe", icon: Settings2, testId: "nav-tariffe" },
];

export default function Layout() {
  const loc = useLocation();
  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border/60 bg-card">
        <div className="px-6 py-7 border-b border-border/60">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-md bg-primary text-primary-foreground grid place-items-center">
              <Sailboat className="w-5 h-5" strokeWidth={2.2} />
            </div>
            <div>
              <div className="font-display text-lg font-semibold leading-none">Portomare</div>
              <div className="label-mini mt-1">Gestione Cantiere</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={n.testId}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-foreground/70 hover:bg-muted hover:text-foreground"
                  )
                }
              >
                <Icon className="w-4 h-4" strokeWidth={2} />
                {n.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border/60">
          <div className="label-mini mb-1">Capacità</div>
          <div className="font-mono-num text-2xl font-semibold">200</div>
          <div className="text-xs text-muted-foreground">posti barca totali</div>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border/60 z-30">
        <div className="grid grid-cols-4">
          {nav.map((n) => {
            const Icon = n.icon;
            const active = loc.pathname === n.to;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`${n.testId}-mobile`}
                className={cn(
                  "flex flex-col items-center gap-1 py-2.5 text-[10px]",
                  active ? "text-primary" : "text-muted-foreground"
                )}
              >
                <Icon className="w-5 h-5" />
                {n.label}
              </NavLink>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 min-w-0 pb-20 md:pb-0">
        <div className="md:hidden px-5 py-4 border-b border-border/60 bg-card flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-primary text-primary-foreground grid place-items-center">
            <Sailboat className="w-4 h-4" />
          </div>
          <div className="font-display text-base font-semibold">Portomare</div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
