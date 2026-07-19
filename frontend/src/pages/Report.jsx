import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Anchor, Waves, Wrench, Sparkles, TrendingUp, FileBarChart,
  Container, Cog, Droplets, ShieldAlert
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, Legend } from "recharts";

const CAT_COLORS = ["#B0562E", "#0F1B3D", "#D9A05B", "#4A6FA5", "#6B8E4E", "#8E6B4E", "#3E5C7E", "#7A4A3E"];

const CATEGORIES = [
  { key: "sosta",                 label: "Incasso sosta",                icon: Anchor,       color: CAT_COLORS[0] },
  { key: "movimentazione_taccaggio", label: "Movimentazione & taccaggio", icon: Container,    color: CAT_COLORS[1] },
  { key: "alaggio_varo",          label: "Incasso alaggio e varo",       icon: Waves,        color: CAT_COLORS[2] },
  { key: "coperture",             label: "Incasso coperture",            icon: Sparkles,     color: CAT_COLORS[3] },
  { key: "antivegetativa",        label: "Incasso antivegetativa",       icon: Droplets,     color: CAT_COLORS[4] },
  { key: "scafo_sporco",          label: "Magg. scafo sporco",           icon: ShieldAlert,  color: CAT_COLORS[5] },
  { key: "lavaggi",               label: "Incasso lavaggi stagionali",   icon: Droplets,     color: CAT_COLORS[6] },
  { key: "manutenzione_motore",   label: "Incasso manutenzione motori",  icon: Wrench,       color: CAT_COLORS[7] },
];

export default function Report() {
  const [r, setR] = useState(null);

  useEffect(() => {
    api.get("/report/incassi").then((res) => setR(res.data));
  }, []);

  if (!r) {
    return <div className="p-8 text-muted-foreground" data-testid="report-loading">Caricamento report…</div>;
  }

  const pieData = CATEGORIES
    .map((c) => ({ name: c.label, value: r.categorie[c.key], color: c.color }))
    .filter((d) => d.value > 0);

  const tipoSostaBar = [
    { label: "Coperto", value: r.per_tipo_sosta.dentro || 0 },
    { label: "A terra", value: r.per_tipo_sosta.fuori || 0 },
    { label: "Fuori sede", value: r.per_tipo_sosta.fuori_sede || 0 },
  ];

  return (
    <div className="p-6 md:p-10 max-w-7xl" data-testid="report-page">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 label-mini mb-2">
            <FileBarChart className="w-3.5 h-3.5" /> Report finanziario
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Sommatoria incassi</h1>
          <p className="text-muted-foreground mt-1">
            Aggregazione entrate per categoria su tutti i {r.totale_clienti} clienti registrati.
          </p>
        </div>
        <div className="text-right">
          <div className="label-mini">Totale generale</div>
          <div className="font-display font-mono-num text-4xl font-bold text-primary mt-1" data-testid="totale-generale">
            {fmtEuro(r.totale)}
          </div>
        </div>
      </div>

      {/* Grid categorie */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const value = r.categorie[cat.key] || 0;
          const pct = r.totale > 0 ? Math.round((value / r.totale) * 100) : 0;
          return (
            <Card key={cat.key} className="p-5 relative overflow-hidden" data-testid={`card-${cat.key}`}>
              <div className="absolute top-0 left-0 h-1 w-full" style={{ background: cat.color }} />
              <div className="flex items-start justify-between mb-3 mt-1">
                <div className="label-mini">{cat.label}</div>
                <Icon className="w-4 h-4 text-muted-foreground shrink-0" strokeWidth={2} />
              </div>
              <div className="font-display text-2xl font-semibold font-mono-num" data-testid={`value-${cat.key}`}>
                {fmtEuro(value)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {pct}% del totale
              </div>
            </Card>
          );
        })}
      </div>

      {/* Grafici + dettagli */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className="p-6" data-testid="chart-categorie">
          <div className="label-mini mb-1">Ripartizione entrate</div>
          <div className="font-display text-xl font-semibold mb-4">Per categoria di servizio</div>
          {pieData.length === 0 ? (
            <div className="h-64 grid place-items-center text-muted-foreground text-sm">Nessun dato disponibile</div>
          ) : (
            <>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value">
                      {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip formatter={(v) => fmtEuro(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-4">
                {pieData.map((d) => (
                  <span key={d.name} className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm" style={{ background: d.color }} />
                    <span className="truncate">{d.name}</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card className="p-6" data-testid="chart-tipo-sosta">
          <div className="label-mini mb-1">Entrate per tipo sosta</div>
          <div className="font-display text-xl font-semibold mb-4">Coperto · A terra · Fuori sede</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tipoSostaBar}>
                <XAxis dataKey="label" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <Tooltip formatter={(v) => fmtEuro(v)} />
                <Bar dataKey="value" fill="hsl(15 55% 45%)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Dettagli sotto-categorie */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DetailCard title="Dettaglio sosta" icon={Anchor} testId="detail-sosta"
          items={[
            { label: "Sosta al coperto / a terra", value: r.sosta_dettaglio.sosta },
            { label: "Movimentazione (fuori sede)", value: r.sosta_dettaglio.movimentazione },
            { label: "Taccaggio (fuori sede)", value: r.sosta_dettaglio.taccaggio },
          ]}
        />
        <DetailCard title="Dettaglio alaggio e varo" icon={Waves} testId="detail-alaggio"
          items={[
            { label: "Alaggio", value: r.alaggio_varo_dettaglio.alaggio },
            { label: "Varo", value: r.alaggio_varo_dettaglio.varo },
          ]}
        />
        <DetailCard title="Dettaglio manutenzione motori" icon={Cog} testId="detail-motore"
          items={[
            { label: "Manodopera motore", value: r.motore_dettaglio.manodopera },
            { label: "Ricambi (totale)", value: r.motore_dettaglio.ricambi },
          ]}
        />
        <DetailCard title="Dettaglio lavaggi" icon={Droplets} testId="detail-lavaggi"
          items={[
            { label: "Inizio stagione", value: r.lavaggi_dettaglio.inizio_stagione },
            { label: "Fine stagione", value: r.lavaggi_dettaglio.fine_stagione },
          ]}
        />
      </div>
    </div>
  );
}

function DetailCard({ title, icon: Icon, items, testId }) {
  const tot = items.reduce((s, i) => s + (i.value || 0), 0);
  return (
    <Card className="p-6" data-testid={testId}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-md bg-primary/10 text-primary grid place-items-center">
          <Icon className="w-4 h-4" />
        </div>
        <div className="font-display text-base font-semibold">{title}</div>
      </div>
      <div className="divide-y divide-border/60">
        {items.map((i) => (
          <div key={i.label} className="py-2.5 flex justify-between items-baseline text-sm">
            <span className="text-foreground/80">{i.label}</span>
            <span className="font-mono-num font-medium">{fmtEuro(i.value)}</span>
          </div>
        ))}
        <div className="pt-3 flex justify-between items-baseline">
          <span className="label-mini">Subtotale</span>
          <span className="font-mono-num font-semibold text-primary">{fmtEuro(tot)}</span>
        </div>
      </div>
    </Card>
  );
}
