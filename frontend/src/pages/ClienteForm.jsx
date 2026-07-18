import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { toast } from "sonner";

const empty = {
  nome: "", cognome: "", tipo_barca: "", lunghezza: 8,
  tipo_sosta: "dentro", posto_barca: "",
  telefono: "", email: "",
  override_costi: false,
  costo_sosta: 0, costo_copertura: 0, costo_alaggio: 0,
  costo_varo: 0, costo_antivegetativa: 0, costo_manutenzione_motore: 0,
  note_lavori: "",
  scadenza_antivegetativa: "", scadenza_manutenzione: "",
};

export default function ClienteForm({ open, onOpenChange, cliente, onSaved }) {
  const [f, setF] = useState(empty);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (cliente) {
      setF({
        ...empty,
        ...cliente,
        posto_barca: cliente.posto_barca ?? "",
        scadenza_antivegetativa: cliente.scadenza_antivegetativa ?? "",
        scadenza_manutenzione: cliente.scadenza_manutenzione ?? "",
      });
    } else {
      setF(empty);
    }
  }, [cliente, open]);

  // Ricalcolo automatico costi quando cambiano lunghezza o tipo_sosta e override off
  useEffect(() => {
    if (!open || f.override_costi) return;
    if (!f.lunghezza || f.lunghezza <= 0) return;
    const t = setTimeout(() => {
      api.get(`/calcola-costi?lunghezza=${f.lunghezza}&tipo_sosta=${f.tipo_sosta}`)
        .then((r) => setF((prev) => ({ ...prev, ...r.data })))
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [f.lunghezza, f.tipo_sosta, f.override_costi, open]);

  const update = (k, v) => setF((prev) => ({ ...prev, [k]: v }));

  const totale =
    (Number(f.costo_sosta) || 0) + (Number(f.costo_copertura) || 0) +
    (Number(f.costo_alaggio) || 0) + (Number(f.costo_varo) || 0) +
    (Number(f.costo_antivegetativa) || 0) + (Number(f.costo_manutenzione_motore) || 0);

  const save = async () => {
    if (!f.nome || !f.cognome || !f.tipo_barca || !f.lunghezza) {
      toast.error("Compila nome, cognome, tipo barca e lunghezza");
      return;
    }
    setSaving(true);
    const payload = {
      ...f,
      lunghezza: Number(f.lunghezza),
      posto_barca: f.posto_barca === "" ? null : Number(f.posto_barca),
      costo_sosta: Number(f.costo_sosta) || 0,
      costo_copertura: Number(f.costo_copertura) || 0,
      costo_alaggio: Number(f.costo_alaggio) || 0,
      costo_varo: Number(f.costo_varo) || 0,
      costo_antivegetativa: Number(f.costo_antivegetativa) || 0,
      costo_manutenzione_motore: Number(f.costo_manutenzione_motore) || 0,
      scadenza_antivegetativa: f.scadenza_antivegetativa || null,
      scadenza_manutenzione: f.scadenza_manutenzione || null,
    };
    try {
      if (cliente?.id) {
        await api.put(`/clienti/${cliente.id}`, payload);
        toast.success("Cliente aggiornato");
      } else {
        await api.post("/clienti", payload);
        toast.success("Cliente creato");
      }
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore durante il salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const isFuori = f.tipo_sosta === "fuori";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto" data-testid="cliente-form">
        <SheetHeader>
          <SheetTitle className="font-display text-2xl">
            {cliente ? "Modifica cliente" : "Nuovo cliente"}
          </SheetTitle>
          <SheetDescription>
            Compila i dati del cliente. I costi vengono calcolati automaticamente in base alle tariffe.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {/* Anagrafica */}
          <section>
            <div className="label-mini mb-3">Anagrafica</div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nome *">
                <Input value={f.nome} onChange={(e) => update("nome", e.target.value)} data-testid="input-nome" />
              </Field>
              <Field label="Cognome *">
                <Input value={f.cognome} onChange={(e) => update("cognome", e.target.value)} data-testid="input-cognome" />
              </Field>
              <Field label="Telefono">
                <Input value={f.telefono} onChange={(e) => update("telefono", e.target.value)} data-testid="input-telefono" />
              </Field>
              <Field label="Email">
                <Input type="email" value={f.email} onChange={(e) => update("email", e.target.value)} data-testid="input-email" />
              </Field>
            </div>
          </section>

          <Separator />

          {/* Barca */}
          <section>
            <div className="label-mini mb-3">Imbarcazione</div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Tipo barca *">
                <Input placeholder="es. Cabinato, Gommone, Yacht…" value={f.tipo_barca} onChange={(e) => update("tipo_barca", e.target.value)} data-testid="input-tipo-barca" />
              </Field>
              <Field label="Lunghezza (metri) *">
                <Input type="number" step="0.1" min="0" value={f.lunghezza} onChange={(e) => update("lunghezza", e.target.value)} data-testid="input-lunghezza" />
              </Field>
              <Field label="Tipo sosta *">
                <Select value={f.tipo_sosta} onValueChange={(v) => update("tipo_sosta", v)}>
                  <SelectTrigger data-testid="select-tipo-sosta"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dentro">In acqua (dentro)</SelectItem>
                    <SelectItem value="fuori">A terra (fuori)</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Posto barca (1-200)">
                <Input type="number" min="1" max="200" placeholder="Assegna dopo…" value={f.posto_barca} onChange={(e) => update("posto_barca", e.target.value)} data-testid="input-posto-barca" />
              </Field>
            </div>
          </section>

          <Separator />

          {/* Costi */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="label-mini">Costi</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {f.override_costi ? "Modifica manuale attiva" : "Calcolati da lunghezza × tariffa"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="override" className="text-sm">Modifica manuale</Label>
                <Switch id="override" checked={f.override_costi} onCheckedChange={(v) => update("override_costi", v)} data-testid="switch-override" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <CostField label="Costo sosta" value={f.costo_sosta} onChange={(v) => update("costo_sosta", v)} disabled={!f.override_costi} testId="costo-sosta" />
              <CostField label="Antivegetativa" value={f.costo_antivegetativa} onChange={(v) => update("costo_antivegetativa", v)} disabled={!f.override_costi} testId="costo-antivegetativa" />
              <CostField label="Manutenzione motore" value={f.costo_manutenzione_motore} onChange={(v) => update("costo_manutenzione_motore", v)} disabled={!f.override_costi} testId="costo-manutenzione" />
              {isFuori && <CostField label="Copertura" value={f.costo_copertura} onChange={(v) => update("costo_copertura", v)} disabled={!f.override_costi} testId="costo-copertura" />}
              {isFuori && <CostField label="Alaggio" value={f.costo_alaggio} onChange={(v) => update("costo_alaggio", v)} disabled={!f.override_costi} testId="costo-alaggio" />}
              {isFuori && <CostField label="Varo" value={f.costo_varo} onChange={(v) => update("costo_varo", v)} disabled={!f.override_costi} testId="costo-varo" />}
            </div>

            <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-md flex items-center justify-between">
              <div className="label-mini">Totale annuale stimato</div>
              <div className="font-display text-2xl font-semibold text-primary font-mono-num" data-testid="totale-costi">{fmtEuro(totale)}</div>
            </div>
          </section>

          <Separator />

          {/* Lavori & scadenze */}
          <section>
            <div className="label-mini mb-3">Lavori & scadenze</div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <Field label="Prossima antivegetativa">
                <Input type="date" value={f.scadenza_antivegetativa || ""} onChange={(e) => update("scadenza_antivegetativa", e.target.value)} data-testid="input-scadenza-antiveg" />
              </Field>
              <Field label="Prossima manutenzione motore">
                <Input type="date" value={f.scadenza_manutenzione || ""} onChange={(e) => update("scadenza_manutenzione", e.target.value)} data-testid="input-scadenza-motore" />
              </Field>
            </div>
            <Field label="Note lavori eseguiti">
              <Textarea rows={5} placeholder="Storico interventi, materiali usati, osservazioni…" value={f.note_lavori} onChange={(e) => update("note_lavori", e.target.value)} data-testid="input-note" />
            </Field>
          </section>
        </div>

        <SheetFooter className="gap-2 sticky bottom-0 bg-background py-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="btn-annulla">Annulla</Button>
          <Button onClick={save} disabled={saving} className="bg-primary hover:bg-primary/90" data-testid="btn-salva">
            {saving ? "Salvataggio…" : "Salva cliente"}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function CostField({ label, value, onChange, disabled, testId }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</Label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
        <Input
          type="number" step="0.01" min="0"
          disabled={disabled}
          value={value ?? 0}
          onChange={(e) => onChange(e.target.value)}
          className="pl-7 font-mono-num"
          data-testid={`input-${testId}`}
        />
      </div>
    </div>
  );
}
