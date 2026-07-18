import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Settings2, RefreshCw, Save, Waves, Anchor, Wrench, Cog } from "lucide-react";

const GROUPS = [
  {
    title: "Sosta",
    icon: Anchor,
    fields: [
      { key: "sosta_dentro_per_metro", label: "Sosta in acqua (dentro)", desc: "€ / metro / anno" },
      { key: "sosta_fuori_per_metro", label: "Sosta a terra (fuori)", desc: "€ / metro / anno" },
    ],
  },
  {
    title: "Alaggio & Varo",
    icon: Waves,
    fields: [
      { key: "alaggio_fino_5m", label: "Alaggio · fino a 5 m", desc: "Forfait per barche ≤ 5 m" },
      { key: "alaggio_oltre_5m_per_metro", label: "Alaggio · oltre 5 m", desc: "€ / metro (per L > 5m)" },
      { key: "varo_fino_5m", label: "Varo · fino a 5 m", desc: "Forfait per barche ≤ 5 m" },
      { key: "varo_oltre_5m_per_metro", label: "Varo · oltre 5 m", desc: "€ / metro (per L > 5m)" },
    ],
  },
  {
    title: "Copertura & Antivegetativa",
    icon: Waves,
    fields: [
      { key: "copertura_per_metro", label: "Copertura", desc: "€ / metro (solo sosta fuori)" },
      { key: "antivegetativa_per_metro", label: "Antivegetativa", desc: "€ / metro" },
    ],
  },
  {
    title: "Manodopera motore (per potenza HP)",
    icon: Wrench,
    fields: [
      { key: "motore_labor_fino_40hp", label: "Fino a 40 HP", desc: "Costo manodopera fisso" },
      { key: "motore_labor_40_150hp", label: "Tra 40 e 150 HP", desc: "Costo manodopera fisso" },
      { key: "motore_labor_oltre_150hp", label: "Oltre 150 HP", desc: "Costo manodopera fisso" },
    ],
  },
  {
    title: "Ricambi motore",
    icon: Cog,
    fields: [
      { key: "costo_girante", label: "Girante", desc: "Costo unitario" },
      { key: "costo_olio_motore", label: "Olio motore", desc: "Costo unitario" },
      { key: "costo_filtro_olio", label: "Filtro olio", desc: "Costo unitario" },
      { key: "costo_candela", label: "Candela", desc: "€ per candela (× numero candele)" },
      { key: "costo_termostato", label: "Termostato", desc: "€ per termostato (× numero termostati)" },
      { key: "costo_olio_piede", label: "Olio piede", desc: "Costo unitario" },
    ],
  },
];

const ALL_KEYS = GROUPS.flatMap((g) => g.fields.map((f) => f.key));

export default function Tariffe() {
  const [t, setT] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/tariffe").then((r) => setT(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      ALL_KEYS.forEach((k) => { payload[k] = Number(t[k]) || 0; });
      await api.put("/tariffe", payload);
      toast.success("Tariffe aggiornate");
      load();
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  if (!t) return <div className="p-8 text-muted-foreground">Caricamento…</div>;

  // Simulazione barca 8m, 120 HP, 4 candele, 1 termostato, sosta fuori
  const L = 8, HP = 120, NC = 4, NT = 1;
  const alaggio = L <= 5 ? t.alaggio_fino_5m : L * t.alaggio_oltre_5m_per_metro;
  const varo = L <= 5 ? t.varo_fino_5m : L * t.varo_oltre_5m_per_metro;
  const labor = HP <= 40 ? t.motore_labor_fino_40hp
    : HP <= 150 ? t.motore_labor_40_150hp
    : t.motore_labor_oltre_150hp;
  const ricambi = Number(t.costo_girante) + Number(t.costo_olio_motore) + Number(t.costo_filtro_olio)
    + NC * Number(t.costo_candela) + NT * Number(t.costo_termostato) + Number(t.costo_olio_piede);
  const motore = Number(labor) + ricambi;
  const totale = L * Number(t.sosta_fuori_per_metro) + L * Number(t.copertura_per_metro)
    + alaggio + varo + L * Number(t.antivegetativa_per_metro) + motore;

  return (
    <div className="p-6 md:p-10 max-w-6xl" data-testid="tariffe-page">
      <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 label-mini mb-2">
            <Settings2 className="w-3.5 h-3.5" /> Configurazione
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Tariffe base</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl">
            Configurazione tariffe con scaglioni per lunghezza (alaggio/varo) e potenza motore (manodopera).
            I ricambi motore sono a costo unitario, moltiplicato per la quantità (candele/termostati) del cliente.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} data-testid="btn-reset">
            <RefreshCw className="w-4 h-4 mr-2" /> Ricarica
          </Button>
          <Button onClick={save} disabled={saving} className="bg-primary hover:bg-primary/90" data-testid="btn-salva-tariffe">
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Salvataggio…" : "Salva tariffe"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {GROUPS.map((g) => {
            const Icon = g.icon;
            return (
              <Card key={g.title} className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-md bg-primary/10 text-primary grid place-items-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="font-display text-base font-semibold">{g.title}</div>
                </div>
                <div className="space-y-2">
                  {g.fields.map((f, i) => (
                    <div key={f.key}>
                      {i > 0 && <Separator className="my-2" />}
                      <div className="flex items-center justify-between gap-3" data-testid={`tariffa-row-${f.key}`}>
                        <div className="min-w-0">
                          <Label className="text-sm font-medium">{f.label}</Label>
                          <p className="text-xs text-muted-foreground mt-0.5">{f.desc}</p>
                        </div>
                        <div className="relative w-32 shrink-0">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
                          <Input
                            type="number" step="0.01" min="0"
                            value={t[f.key]}
                            onChange={(e) => setT({ ...t, [f.key]: e.target.value })}
                            className="pl-7 font-mono-num text-right h-9"
                            data-testid={`input-${f.key}`}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            );
          })}
        </div>

        {/* Preview */}
        <Card className="p-6 h-fit sticky top-6 bg-secondary/40" data-testid="preview-tariffe">
          <div className="label-mini mb-3">Simulazione</div>
          <h3 className="font-display text-lg font-semibold mb-1">Barca 8m · 120 HP</h3>
          <p className="text-xs text-muted-foreground mb-5">Sosta fuori, 4 candele, 1 termostato</p>

          <div className="space-y-3 text-sm">
            <PreviewRow label="Sosta fuori" value={L * t.sosta_fuori_per_metro} />
            <PreviewRow label="Copertura" value={L * t.copertura_per_metro} />
            <PreviewRow label="Alaggio (>5m)" value={alaggio} />
            <PreviewRow label="Varo (>5m)" value={varo} />
            <PreviewRow label="Antivegetativa" value={L * t.antivegetativa_per_metro} />
            <div className="pt-2 border-t border-border/60">
              <PreviewRow label="Manodopera motore" value={labor} />
              <PreviewRow label="Ricambi" value={ricambi} muted />
              <PreviewRow label="Motore totale" value={motore} bold />
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-primary/30">
            <div className="label-mini">Totale annuale</div>
            <div className="font-mono-num text-3xl font-bold text-primary mt-1">{fmtEuro(totale)}</div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function PreviewRow({ label, value, bold, muted }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className={`${muted ? "text-muted-foreground text-xs" : ""} ${bold ? "font-semibold" : ""}`}>{label}</span>
      <span className={`font-mono-num ${bold ? "font-semibold" : ""} ${muted ? "text-muted-foreground text-xs" : ""}`}>{fmtEuro(value)}</span>
    </div>
  );
}
