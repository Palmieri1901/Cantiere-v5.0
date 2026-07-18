import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Settings2, RefreshCw, Save } from "lucide-react";

const FIELDS = [
  { key: "sosta_dentro_per_metro", label: "Sosta in acqua (dentro)", desc: "€ al metro, base annuale" },
  { key: "sosta_fuori_per_metro", label: "Sosta a terra (fuori)", desc: "€ al metro, base annuale" },
  { key: "copertura_per_metro", label: "Copertura", desc: "€ al metro, solo sosta fuori" },
  { key: "alaggio_per_metro", label: "Alaggio", desc: "€ al metro" },
  { key: "varo_per_metro", label: "Varo", desc: "€ al metro" },
  { key: "antivegetativa_per_metro", label: "Antivegetativa", desc: "€ al metro" },
  { key: "manutenzione_motore_base", label: "Manutenzione motore", desc: "€ base fisso (non a metro)" },
];

export default function Tariffe() {
  const [t, setT] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/tariffe").then((r) => setT(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach((f) => { payload[f.key] = Number(t[f.key]) || 0; });
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

  // Esempio calcolo su barca da 10m
  const esempio = 10;
  const totaleDentro = t.sosta_dentro_per_metro * esempio + t.antivegetativa_per_metro * esempio + t.manutenzione_motore_base;
  const totaleFuori =
    t.sosta_fuori_per_metro * esempio +
    t.copertura_per_metro * esempio +
    t.alaggio_per_metro * esempio +
    t.varo_per_metro * esempio +
    t.antivegetativa_per_metro * esempio +
    t.manutenzione_motore_base;

  return (
    <div className="p-6 md:p-10 max-w-5xl" data-testid="tariffe-page">
      <div className="mb-8">
        <div className="flex items-center gap-2 label-mini mb-2">
          <Settings2 className="w-3.5 h-3.5" /> Configurazione
        </div>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Tariffe base</h1>
        <p className="text-muted-foreground mt-1 max-w-2xl">
          Le tariffe si applicano automaticamente al calcolo dei costi per ogni cliente.
          È sempre possibile modificare manualmente i valori per singolo cliente attivando l'override.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          {FIELDS.map((f) => (
            <Card key={f.key} className="p-5 flex items-center justify-between gap-4" data-testid={`tariffa-row-${f.key}`}>
              <div className="min-w-0">
                <Label className="text-base font-medium">{f.label}</Label>
                <p className="text-xs text-muted-foreground mt-1">{f.desc}</p>
              </div>
              <div className="relative w-40 shrink-0">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
                <Input
                  type="number" step="0.01" min="0"
                  value={t[f.key]}
                  onChange={(e) => setT({ ...t, [f.key]: e.target.value })}
                  className="pl-7 font-mono-num text-right"
                  data-testid={`input-${f.key}`}
                />
              </div>
            </Card>
          ))}

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={load} data-testid="btn-reset">
              <RefreshCw className="w-4 h-4 mr-2" /> Ricarica
            </Button>
            <Button onClick={save} disabled={saving} className="bg-primary hover:bg-primary/90" data-testid="btn-salva-tariffe">
              <Save className="w-4 h-4 mr-2" />
              {saving ? "Salvataggio…" : "Salva tariffe"}
            </Button>
          </div>
        </div>

        {/* Preview */}
        <Card className="p-6 h-fit sticky top-6 bg-secondary/40" data-testid="preview-tariffe">
          <div className="label-mini mb-3">Esempio: barca da {esempio}m</div>
          <h3 className="font-display text-lg font-semibold mb-4">Simulazione costi</h3>

          <div className="mb-5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Sosta dentro</div>
            <div className="font-mono-num text-2xl font-semibold text-foreground">{fmtEuro(totaleDentro)}</div>
            <div className="text-xs text-muted-foreground mt-1">Sosta + antivegetativa + motore</div>
          </div>

          <div className="border-t pt-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Sosta fuori</div>
            <div className="font-mono-num text-2xl font-semibold text-primary">{fmtEuro(totaleFuori)}</div>
            <div className="text-xs text-muted-foreground mt-1">Include copertura, alaggio, varo</div>
          </div>
        </Card>
      </div>
    </div>
  );
}
