import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { useYear } from "@/lib/year";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Anchor, Waves, Wrench, CalendarClock, TrendingUp, Users } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

const COLORS = ["hsl(15 55% 45%)", "hsl(225 60% 25%)", "hsl(40 60% 55%)"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const { year } = useYear();

  useEffect(() => {
    api.get(`/stats?anno=${year}`).then((r) => setStats(r.data));
  }, [year]);

  if (!stats) {
    return (
      <div className="p-8" data-testid="dashboard-loading">
        <div className="animate-pulse text-muted-foreground">Caricamento…</div>
      </div>
    );
  }

  const occupancyPct = Math.round((stats.posti_occupati / stats.posti_totali) * 100);
  const pieData = [
    { name: "Al coperto", value: stats.sosta_dentro },
    { name: "Sosta Fuori", value: stats.sosta_fuori },
    { name: "Liberi", value: stats.posti_liberi },
  ];

  const barData = [
    { label: "Occupati", value: stats.posti_occupati },
    { label: "Liberi", value: stats.posti_liberi },
  ];

  return (
    <div className="p-6 md:p-10 max-w-7xl" data-testid="dashboard-page">
      {/* Header */}
      <div className="mb-10">
        <div className="label-mini mb-3">Panoramica cantiere</div>
        <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight text-foreground">
          Buongiorno, comandante.
        </h1>
        <p className="text-muted-foreground mt-2 max-w-2xl">
          Stato attuale del cantiere: {stats.posti_occupati} barche in gestione su {stats.posti_totali} posti disponibili.
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={Anchor}
          label="Posti Occupati"
          value={`${stats.posti_occupati} / ${stats.posti_totali}`}
          sub={`${occupancyPct}% di occupazione`}
          testId="stat-occupati"
        />
        <StatCard
          icon={Users}
          label="Clienti Totali"
          value={stats.totale_clienti}
          sub={`${stats.sosta_dentro} dentro · ${stats.sosta_fuori} fuori`}
          testId="stat-clienti"
        />
        <StatCard
          icon={TrendingUp}
          label="Entrate Stimate"
          value={fmtEuro(stats.entrate_totali)}
          sub="Somma costi in gestione"
          testId="stat-entrate"
          highlight
        />
        <StatCard
          icon={CalendarClock}
          label="Scadenze 30gg"
          value={stats.scadenze_prossime.length}
          sub="Interventi da pianificare"
          testId="stat-scadenze"
        />
      </div>

      {/* Occupancy bar */}
      <Card className="p-6 mb-8" data-testid="occupancy-card">
        <div className="flex items-baseline justify-between mb-3">
          <div>
            <div className="label-mini">Occupazione</div>
            <div className="font-display text-2xl font-semibold mt-1">
              {stats.posti_occupati} <span className="text-muted-foreground text-lg">/ {stats.posti_totali} posti</span>
            </div>
          </div>
          <div className="font-mono-num text-3xl font-bold text-primary">{occupancyPct}%</div>
        </div>
        <Progress value={occupancyPct} className="h-2" />
        <div className="flex gap-6 mt-4 text-sm">
          <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-primary" />Occupati</span>
          <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-muted" />Liberi</span>
        </div>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <Card className="p-6" data-testid="chart-distribution">
          <div className="label-mini mb-1">Distribuzione soste</div>
          <div className="font-display text-xl font-semibold mb-4">Dentro vs Fuori vs Liberi</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value">
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 text-xs mt-2">
            {pieData.map((d, i) => (
              <span key={d.name} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm" style={{ background: COLORS[i] }} />
                {d.name}: <b className="font-mono-num">{d.value}</b>
              </span>
            ))}
          </div>
        </Card>

        <Card className="p-6" data-testid="chart-posti">
          <div className="label-mini mb-1">Posti barca</div>
          <div className="font-display text-xl font-semibold mb-4">Occupati e liberi</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <XAxis dataKey="label" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <Tooltip />
                <Bar dataKey="value" fill="hsl(15 55% 45%)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Scadenze */}
      <Card className="p-6" data-testid="scadenze-card">
        <div className="flex items-center gap-2 mb-4">
          <Wrench className="w-4 h-4 text-primary" />
          <div className="label-mini">Prossime scadenze (30 giorni)</div>
        </div>
        {stats.scadenze_prossime.length === 0 ? (
          <div className="text-sm text-muted-foreground py-6 text-center">Nessuna scadenza nei prossimi 30 giorni.</div>
        ) : (
          <div className="divide-y divide-border/60">
            {stats.scadenze_prossime.map((s, i) => (
              <div key={i} className="py-3 flex items-center justify-between" data-testid={`scadenza-${i}`}>
                <div>
                  <div className="font-medium">{s.nome}</div>
                  <div className="text-xs text-muted-foreground">{s.tipo} · {s.data}</div>
                </div>
                <Badge variant={s.giorni_rimanenti <= 7 ? "destructive" : "secondary"}>
                  {s.giorni_rimanenti === 0 ? "Oggi" : `${s.giorni_rimanenti} gg`}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub, testId, highlight }) {
  return (
    <Card className={`p-5 relative ${highlight ? "border-primary/40 bg-primary/5" : ""}`} data-testid={testId}>
      <div className="flex items-start justify-between mb-3">
        <div className="label-mini">{label}</div>
        <Icon className={`w-4 h-4 ${highlight ? "text-primary" : "text-muted-foreground"}`} strokeWidth={2} />
      </div>
      <div className="font-display text-3xl font-semibold tracking-tight font-mono-num">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{sub}</div>
    </Card>
  );
}
