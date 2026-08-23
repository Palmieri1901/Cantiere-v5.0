import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Settings2, RefreshCw, Save, Waves, Anchor, Wrench, Cog } from "lucide-react";
import { useYear } from "@/lib/year";

const GROUPS = [
  {
    title: "Sosta",
    icon: Anchor,
    fields: [
      { key: "sosta_dentro_per_metro", label: "Sosta al coperto", desc: "€ / metro / anno (posto coperto/dentro)" },
      { key: "sosta_fuori_per_metro", label: "Sosta su piazzale (fuori)", desc: "€ / metro / anno" },
      { key: "sosta_temporanea_giornaliera", label: "Sosta temporanea", desc: "€ al mt / giorno" },
      { key: "costo_movimentazione_per_metro", label: "Movimentazione (fuori sede)", desc: "€ / metro (sosta fuori sede)" },
      { key: "costo_taccaggio_per_metro", label: "Taccaggio (fuori sede)", desc: "€ / metro (sosta fuori sede)" },
    ],
  },
  {
    title: "Alaggio & Varo",
    icon: Waves,
    fields: [
      { key: "alaggio_fino_5m", label: "Alaggio · fino a 5 m", desc: "Forfait per barche ≤ 5 m" },
      { key: "alaggio_oltre_5m_per_metro", label: "Alaggio · oltre 5 m", desc: "Forfait per barche > 5 m" },
      { key: "varo_fino_5m", label: "Varo · fino a 5 m", desc: "Forfait per barche ≤ 5 m" },
      { key: "varo_oltre_5m_per_metro", label: "Varo · oltre 5 m", desc: "Forfait per barche > 5 m" },
    ],
  },
  {
    title: "Copertura & Antivegetativa",
    icon: Waves,
    fields: [
      { key: "copertura_per_metro", label: "Copertura", desc: "€ / metro (solo sosta fuori)" },
      { key: "antivegetativa_per_metro", label: "Antivegetativa", desc: "€ / metro" },
      { key: "maggiorazione_scafo_sporco_per_metro", label: "Magg. scafo sporco", desc: "€ / metro (se antivegetativa disattivata)" },
    ],
  },
  {
    title: "Lavaggi stagionali",
    icon: Waves,
    fields: [
      { key: "costo_lavaggio_inizio_stagione", label: "Lavaggio inizio stagione", desc: "€ / metro" },
      { key: "costo_lavaggio_fine_stagione", label: "Lavaggio fine stagione", desc: "€ / metro" },
    ],
  },
  {
    title: "Manodopera motore",
    icon: Wrench,
    fields: [
      { key: "motore_labor", label: "Manodopera motore", desc: "Tariffa unica valida per qualsiasi HP" },
      { key: "maggiorazione_entrobordo", label: "Maggiorazione entrobordo", desc: "€ aggiunto alla manodopera se motore entrobordo" },
    ],
  },
  {
    title: "Ricambi motore",
    icon: Cog,
    fields: [
      { key: "costo_girante", label: "Girante", desc: "Costo unitario" },
      { key: "costo_olio_motore", label: "Olio motore", desc: "€ / litro (× litri motore cliente)" },
      { key: "costo_filtro_olio", label: "Filtro olio", desc: "Costo unitario" },
      { key: "costo_candela", label: "Candela", desc: "€ per candela (× numero candele)" },
      { key: "costo_termostato", label: "Termostato", desc: "€ per termostato (× numero termostati)" },
      { key: "costo_olio_piede", label: "Olio piede", desc: "Costo per litro" },
      { key: "costo_anodi_interni", label: "Kit anodi interni", desc: "Costo unitario" },
      { key: "costo_anodi_esterni", label: "Kit anodi esterni", desc: "Costo unitario" },
      { key: "costo_ingrassaggio", label: "Ingrassaggio", desc: "Costo unitario" },
    ],
  },
];

const ALL_KEYS = GROUPS.flatMap((g) => g.fields.map((f) => f.key));

export default function Tariffe() {
  const [t, setT] = useState(null);
  const [saving, setSaving] = useState(false);
  const { year } = useYear();

  const load = () => api.get("/tariffe").then((r) => setT(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      ALL_KEYS.forEach((k) => { payload[k] = Number(t[k]) || 0; });
      await api.put("/tariffe", payload);
      // Ricalcolo automatico di tutti i clienti dell'anno in corso
      try {
        const r = await api.post(`/tariffe/ricalcola?anno=${year}`);
        const { aggiornati, totali } = r.data || {};
        toast.success(`Tariffe aggiornate · ${aggiornati}/${totali} clienti ${year} ricalcolati`);
      } catch {
        toast.success("Tariffe aggiornate (ricalcolo clienti non riuscito)");
      }
      load();
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  if (!t) return <div className="p-8 text-muted-foreground">Caricamento…</div>;

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

      <div className="grid grid-cols-1 gap-6">
        <div className="space-y-6">
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
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
                          <Input
                            type="number" step="0.01" min="0"
                            value={t[f.key]}
                            onChange={(e) => setT({ ...t, [f.key]: e.target.value })}
                            className="pl-10 font-mono-num text-right h-9"
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
      </div>
    </div>
  );
}
