import { useEffect, useState } from "react";
import { api, fmtEuro, API } from "@/lib/api";
import { useYear } from "@/lib/year";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  Anchor, Waves, Wrench, Sparkles, TrendingUp, FileBarChart,
  Container, Cog, Droplets, ShieldAlert, CheckCircle2, XCircle, FileDown
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, Legend } from "recharts";

const CAT_COLORS = ["#B0562E", "#0F1B3D", "#D9A05B", "#4A6FA5", "#6B8E4E", "#8E6B4E", "#3E5C7E", "#7A4A3E", "#5A7A9A"];

const CATEGORIES = [
  { key: "sosta",                 label: "Incasso sosta",                icon: Anchor,       color: CAT_COLORS[0] },
  { key: "movimentazione_taccaggio", label: "Movimentazione & taccaggio", icon: Container,    color: CAT_COLORS[1] },
  { key: "alaggio_varo",          label: "Incasso alaggio e varo",       icon: Waves,        color: CAT_COLORS[2] },
  { key: "coperture",             label: "Incasso coperture",            icon: Sparkles,     color: CAT_COLORS[3] },
  { key: "antivegetativa",        label: "Incasso antivegetativa",       icon: Droplets,     color: CAT_COLORS[4] },
  { key: "scafo_sporco",          label: "Magg. scafo sporco",           icon: ShieldAlert,  color: CAT_COLORS[5] },
  { key: "lavaggi",               label: "Incasso lavaggi stagionali",   icon: Droplets,     color: CAT_COLORS[6] },
  { key: "manutenzione_motore",   label: "Incasso manutenzione motori",  icon: Wrench,       color: CAT_COLORS[7] },
  { key: "lavorazioni_extra",     label: "Lavorazioni extra",            icon: Wrench,       color: CAT_COLORS[8] },
];

export default function Report() {
  const [r, setR] = useState(null);
  const [pagamenti, setPagamenti] = useState(null);
  const [filtroStato, setFiltroStato] = useState("tutti"); // tutti | pagati | non_pagati
  const { year } = useYear();

  const loadAll = () => {
    api.get(`/report/incassi?anno=${year}`).then((res) => setR(res.data));
    api.get(`/report/pagamenti?anno=${year}`).then((res) => setPagamenti(res.data));
  };

  useEffect(() => { loadAll(); }, [year]);

  const togglePagato = async (id, nuovoStato) => {
    try {
      await api.patch(`/clienti/${id}/pagato`, { pagato: nuovoStato });
      toast.success(nuovoStato ? "Segnato come pagato" : "Segnato come non pagato");
      loadAll();
    } catch {
      toast.error("Errore aggiornamento");
    }
  };

  if (!r) {
    return <div className="p-8 text-muted-foreground" data-testid="report-loading">Caricamento report…</div>;
  }

  const pieData = CATEGORIES
    .map((c) => ({ name: c.label, value: r.categorie[c.key], color: c.color }))
    .filter((d) => d.value > 0);

  const tipoSostaBar = [
    { label: "Coperto", value: r.per_tipo_sosta.dentro || 0 },
    { label: "Su piazzale", value: r.per_tipo_sosta.fuori || 0 },
    { label: "Fuori sede", value: r.per_tipo_sosta.fuori_sede || 0 },
    { label: "Temporanea", value: r.per_tipo_sosta.temporanea || 0 },
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
          <div className="font-display text-xl font-semibold mb-4">Coperto · Su piazzale · Fuori sede</div>
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

      {/* Tabella pagamenti */}
      {pagamenti && (
        <Card className="p-6 mt-6" data-testid="card-pagamenti">
          <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
            <div>
              <div className="label-mini mb-1">Stato pagamenti</div>
              <h3 className="font-display text-xl font-semibold">Chi ha pagato · Chi deve ancora</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Clicca sul pulsante per cambiare lo stato di pagamento del cliente.
              </p>
            </div>
            <div className="flex gap-4 text-sm">
              <div className="text-right">
                <div className="label-mini text-emerald-700">Pagato</div>
                <div className="font-mono-num text-xl font-bold text-emerald-700" data-testid="totale-pagato">
                  {fmtEuro(pagamenti.totale_pagato)}
                </div>
                <div className="text-[11px] text-muted-foreground">{pagamenti.numero_pagati} clienti</div>
              </div>
              <div className="text-right">
                <div className="label-mini text-destructive">Da incassare</div>
                <div className="font-mono-num text-xl font-bold text-destructive" data-testid="totale-da-pagare">
                  {fmtEuro(pagamenti.totale_da_pagare)}
                </div>
                <div className="text-[11px] text-muted-foreground">{pagamenti.numero_non_pagati} clienti</div>
              </div>
            </div>
          </div>

          {/* Toolbar filtro + PDF */}
          <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="label-mini">Mostra:</span>
              <Select value={filtroStato} onValueChange={setFiltroStato}>
                <SelectTrigger className="w-48" data-testid="select-filtro-stato">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tutti" data-testid="opt-tutti">Tutti i clienti</SelectItem>
                  <SelectItem value="pagati" data-testid="opt-pagati">Solo pagati</SelectItem>
                  <SelectItem value="non_pagati" data-testid="opt-non-pagati">Solo non pagati</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-xs text-muted-foreground">
                {(() => {
                  const filtrati = pagamenti.clienti.filter((c) =>
                    filtroStato === "tutti" ? true :
                    filtroStato === "pagati" ? c.pagato : !c.pagato
                  );
                  return `${filtrati.length} cliente${filtrati.length === 1 ? "" : "i"}`;
                })()}
              </span>
            </div>
            <Button asChild variant="outline" size="sm" data-testid="btn-scarica-pdf-pagamenti">
              <a href={`${API}/report/pagamenti.pdf?anno=${year}&stato=${filtroStato}`} target="_blank" rel="noreferrer">
                <FileDown className="w-4 h-4 mr-2" />
                Scarica report PDF
              </a>
            </Button>
          </div>

          {pagamenti.clienti.length === 0 ? (
            <div className="text-muted-foreground text-sm py-8 text-center">Nessun cliente per questo anno.</div>
          ) : (
            <div className="border border-border rounded-md overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40">
                    <TableHead>Cliente</TableHead>
                    <TableHead>Barca</TableHead>
                    <TableHead>Sosta</TableHead>
                    <TableHead className="text-right">Totale</TableHead>
                    <TableHead className="w-40 text-center">Stato pagamento</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagamenti.clienti
                    .filter((c) => filtroStato === "tutti" ? true : filtroStato === "pagati" ? c.pagato : !c.pagato)
                    .map((c) => (
                    <TableRow key={c.id} data-testid={`row-pag-${c.id}`}>
                      <TableCell className="font-medium">{c.cognome} {c.nome}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{c.tipo_barca}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {c.tipo_sosta === "dentro" ? "Coperto" : c.tipo_sosta === "fuori_sede" ? "Fuori sede" : c.tipo_sosta === "temporanea" ? "Temporanea" : "Su piazzale"}
                      </TableCell>
                      <TableCell className="text-right font-mono-num font-semibold">{fmtEuro(c.totale)}</TableCell>
                      <TableCell className="text-center">
                        <button
                          onClick={() => togglePagato(c.id, !c.pagato)}
                          className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full font-medium text-sm border-2 transition-all ${
                            c.pagato
                              ? "bg-emerald-500 hover:bg-emerald-600 text-white border-emerald-600"
                              : "bg-destructive hover:bg-destructive/90 text-white border-destructive/70"
                          }`}
                          data-testid={`btn-pagato-${c.id}`}
                          title="Clicca per cambiare stato"
                        >
                          {c.pagato ? (
                            <><CheckCircle2 className="w-4 h-4" /> Pagato</>
                          ) : (
                            <><XCircle className="w-4 h-4" /> Non pagato</>
                          )}
                        </button>
                        {c.pagato && c.data_pagamento && (
                          <div className="text-[10px] text-muted-foreground mt-1 font-mono-num">
                            {c.data_pagamento}
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Card>
      )}
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
