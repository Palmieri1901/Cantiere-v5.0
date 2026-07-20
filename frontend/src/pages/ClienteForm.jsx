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
import LavoriSection from "@/pages/LavoriSection";
import { API } from "@/lib/api";
import { useYear } from "@/lib/year";
import { FileText } from "lucide-react";

const empty = {
  nome: "", cognome: "", tipo_barca: "", lunghezza: 8,
  tipo_sosta: "dentro", posto_barca: "",
  telefono: "", email: "",
  potenza_motore: 0, litri_olio_motore: 3, numero_candele: 4, numero_termostati: 1,
  antivegetativa_attiva: true, girante_attivo: true,
  lavaggio_inizio_attivo: true, lavaggio_fine_attivo: true,
  override_costi: false,
  costo_sosta: 0, costo_copertura: 0, costo_alaggio: 0,
  costo_varo: 0, costo_antivegetativa: 0, costo_manutenzione_motore: 0,
  costo_ricambi_totale: 0, costo_manodopera_motore: 0,
  costo_lavaggio_inizio: 0, costo_lavaggio_fine: 0, costo_scafo_sporco: 0,
  note_lavori: "",
  scadenza_antivegetativa: "", scadenza_manutenzione: "",
};

export default function ClienteForm({ open, onOpenChange, cliente, onSaved }) {
  const [f, setF] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [ricambiDettaglio, setRicambiDettaglio] = useState(null);
  const { year } = useYear();

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
    setRicambiDettaglio(null);
  }, [cliente, open]);

  // Ricalcolo automatico costi
  useEffect(() => {
    if (!open || f.override_costi) return;
    if (!f.lunghezza || f.lunghezza <= 0) return;
    const t = setTimeout(() => {
      const params = new URLSearchParams({
        lunghezza: f.lunghezza,
        tipo_sosta: f.tipo_sosta,
        potenza_motore: f.potenza_motore || 0,
        litri_olio_motore: f.litri_olio_motore || 0,
        numero_candele: f.numero_candele || 0,
        numero_termostati: f.numero_termostati || 0,
        antivegetativa_attiva: f.antivegetativa_attiva ? "true" : "false",
        girante_attivo: f.girante_attivo ? "true" : "false",
        lavaggio_inizio_attivo: f.lavaggio_inizio_attivo ? "true" : "false",
        lavaggio_fine_attivo: f.lavaggio_fine_attivo ? "true" : "false",
      });
      api.get(`/calcola-costi?${params}`)
        .then((r) => {
          const { ricambi_dettaglio, ...rest } = r.data;
          setRicambiDettaglio(ricambi_dettaglio || null);
          setF((prev) => ({ ...prev, ...rest }));
        })
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [f.lunghezza, f.tipo_sosta, f.potenza_motore, f.litri_olio_motore, f.numero_candele, f.numero_termostati, f.antivegetativa_attiva, f.girante_attivo, f.lavaggio_inizio_attivo, f.lavaggio_fine_attivo, f.override_costi, open]);

  const update = (k, v) => setF((prev) => ({ ...prev, [k]: v }));

  const totale =
    (Number(f.costo_sosta) || 0) + (Number(f.costo_copertura) || 0) +
    (Number(f.costo_alaggio) || 0) + (Number(f.costo_varo) || 0) +
    (Number(f.costo_antivegetativa) || 0) + (Number(f.costo_manutenzione_motore) || 0) +
    (Number(f.costo_lavaggio_inizio) || 0) + (Number(f.costo_lavaggio_fine) || 0) +
    (Number(f.costo_scafo_sporco) || 0);

  const save = async () => {
    if (!f.nome || !f.cognome || !f.tipo_barca || !f.lunghezza) {
      toast.error("Compila nome, cognome, tipo barca e lunghezza");
      return;
    }
    setSaving(true);
    const payload = {
      ...f,
      anno: cliente?.anno || year,
      lunghezza: Number(f.lunghezza),
      potenza_motore: Number(f.potenza_motore) || 0,
      litri_olio_motore: Number(f.litri_olio_motore) || 0,
      numero_candele: Number(f.numero_candele) || 0,
      numero_termostati: Number(f.numero_termostati) || 0,
      antivegetativa_attiva: !!f.antivegetativa_attiva,
      girante_attivo: !!f.girante_attivo,
      lavaggio_inizio_attivo: !!f.lavaggio_inizio_attivo,
      lavaggio_fine_attivo: !!f.lavaggio_fine_attivo,
      posto_barca: f.posto_barca === "" ? null : Number(f.posto_barca),
      costo_sosta: Number(f.costo_sosta) || 0,
      costo_copertura: Number(f.costo_copertura) || 0,
      costo_alaggio: Number(f.costo_alaggio) || 0,
      costo_varo: Number(f.costo_varo) || 0,
      costo_antivegetativa: Number(f.costo_antivegetativa) || 0,
      costo_manutenzione_motore: Number(f.costo_manutenzione_motore) || 0,
      costo_lavaggio_inizio: Number(f.costo_lavaggio_inizio) || 0,
      costo_lavaggio_fine: Number(f.costo_lavaggio_fine) || 0,
      costo_scafo_sporco: Number(f.costo_scafo_sporco) || 0,
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
  const isFuoriSede = f.tipo_sosta === "fuori_sede";

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
                    <SelectItem value="dentro">Al coperto (dentro)</SelectItem>
                    <SelectItem value="fuori">A terra (fuori)</SelectItem>
                    <SelectItem value="fuori_sede">Fuori sede</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Posto barca (1-200)">
                <Input type="number" min="1" max="200" placeholder="Assegna dopo…" value={f.posto_barca} onChange={(e) => update("posto_barca", e.target.value)} data-testid="input-posto-barca" />
              </Field>
            </div>
          </section>

          <Separator />

          {/* Motore */}
          <section>
            <div className="label-mini mb-3">Motore</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Field label="Cavalli (HP)">
                <Input type="number" min="0" step="1" value={f.potenza_motore} onChange={(e) => update("potenza_motore", e.target.value)} data-testid="input-potenza-motore" />
              </Field>
              <Field label="Litri olio motore">
                <Input type="number" min="0" step="0.1" value={f.litri_olio_motore} onChange={(e) => update("litri_olio_motore", e.target.value)} data-testid="input-litri-olio" />
              </Field>
              <Field label="N° candele">
                <Input type="number" min="0" step="1" value={f.numero_candele} onChange={(e) => update("numero_candele", e.target.value)} data-testid="input-numero-candele" />
              </Field>
              <Field label="N° termostati">
                <Input type="number" min="0" step="1" value={f.numero_termostati} onChange={(e) => update("numero_termostati", e.target.value)} data-testid="input-numero-termostati" />
              </Field>
            </div>
            <div className="text-[11px] text-muted-foreground mt-2">
              Fasce manodopera: ≤40 HP · 40-150 HP · &gt;150 HP. Olio motore calcolato al litro. I ricambi si moltiplicano per il numero indicato.
            </div>

            {/* Servizi opzionali */}
            <div className="mt-4 grid grid-cols-2 gap-3">
              <ToggleRow
                label="Antivegetativa"
                description="Applica il costo antivegetativa"
                checked={!!f.antivegetativa_attiva}
                onChange={(v) => update("antivegetativa_attiva", v)}
                testId="switch-antivegetativa"
              />
              <ToggleRow
                label="Sostituzione girante"
                description="Includi ricambio girante"
                checked={!!f.girante_attivo}
                onChange={(v) => update("girante_attivo", v)}
                testId="switch-girante"
              />
              <ToggleRow
                label="Lavaggio inizio stagione"
                description="Includi lavaggio a inizio stagione"
                checked={!!f.lavaggio_inizio_attivo}
                onChange={(v) => update("lavaggio_inizio_attivo", v)}
                testId="switch-lavaggio-inizio"
              />
              <ToggleRow
                label="Lavaggio fine stagione"
                description="Includi lavaggio a fine stagione"
                checked={!!f.lavaggio_fine_attivo}
                onChange={(v) => update("lavaggio_fine_attivo", v)}
                testId="switch-lavaggio-fine"
              />
            </div>
            {!f.antivegetativa_attiva && (
              <div className="mt-2 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2" data-testid="info-scafo-sporco">
                Antivegetativa disattivata → viene applicata la maggiorazione scafo sporco (€ / metro).
              </div>
            )}
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
              {!isFuoriSede && (
                <CostField label="Costo sosta" value={f.costo_sosta} onChange={(v) => update("costo_sosta", v)} disabled={!f.override_costi} testId="costo-sosta" />
              )}
              {isFuoriSede && (
                <>
                  <CostField label="Movimentazione" value={f.costo_movimentazione} onChange={(v) => update("costo_movimentazione", v)} disabled={!f.override_costi} testId="costo-movimentazione" />
                  <CostField label="Taccaggio" value={f.costo_taccaggio} onChange={(v) => update("costo_taccaggio", v)} disabled={!f.override_costi} testId="costo-taccaggio" />
                </>
              )}
              <CostField label="Antivegetativa" value={f.costo_antivegetativa} onChange={(v) => update("costo_antivegetativa", v)} disabled={!f.override_costi} testId="costo-antivegetativa" />
              {!f.antivegetativa_attiva && (
                <CostField label="Magg. scafo sporco" value={f.costo_scafo_sporco} onChange={(v) => update("costo_scafo_sporco", v)} disabled={!f.override_costi} testId="costo-scafo-sporco" />
              )}
              <CostField label="Lavaggio inizio stagione" value={f.costo_lavaggio_inizio} onChange={(v) => update("costo_lavaggio_inizio", v)} disabled={!f.override_costi} testId="costo-lavaggio-inizio" />
              <CostField label="Lavaggio fine stagione" value={f.costo_lavaggio_fine} onChange={(v) => update("costo_lavaggio_fine", v)} disabled={!f.override_costi} testId="costo-lavaggio-fine" />
              <CostField label="Manutenzione motore" value={f.costo_manutenzione_motore} onChange={(v) => update("costo_manutenzione_motore", v)} disabled={!f.override_costi} testId="costo-manutenzione" />
              {isFuori && <CostField label="Copertura" value={f.costo_copertura} onChange={(v) => update("costo_copertura", v)} disabled={!f.override_costi} testId="costo-copertura" />}
              {isFuori && <CostField label="Alaggio" value={f.costo_alaggio} onChange={(v) => update("costo_alaggio", v)} disabled={!f.override_costi} testId="costo-alaggio" />}
              {isFuori && <CostField label="Varo" value={f.costo_varo} onChange={(v) => update("costo_varo", v)} disabled={!f.override_costi} testId="costo-varo" />}
            </div>

            {/* Dettaglio motore breakdown */}
            {!f.override_costi && ricambiDettaglio && Number(f.potenza_motore) > 0 && (
              <div className="mt-4 p-3 bg-muted/40 border border-border rounded-md" data-testid="ricambi-breakdown">
                <div className="label-mini mb-2">Dettaglio motore</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <BreakdownRow label="Manodopera" value={f.costo_manodopera_motore} />
                  <BreakdownRow label="Girante" value={ricambiDettaglio.girante} />
                  <BreakdownRow label={`Olio motore (${f.litri_olio_motore || 0}L)`} value={ricambiDettaglio.olio_motore} />
                  <BreakdownRow label="Filtro olio" value={ricambiDettaglio.filtro_olio} />
                  <BreakdownRow label={`Candele (${f.numero_candele || 0})`} value={ricambiDettaglio.candele} />
                  <BreakdownRow label={`Termostati (${f.numero_termostati || 0})`} value={ricambiDettaglio.termostati} />
                  <BreakdownRow label="Olio piede" value={ricambiDettaglio.olio_piede} />
                  <BreakdownRow label="Anodi interni" value={ricambiDettaglio.anodi_interni} />
                  <BreakdownRow label="Anodi esterni" value={ricambiDettaglio.anodi_esterni} />
                  <BreakdownRow label="Ingrassaggio" value={ricambiDettaglio.ingrassaggio} />
                </div>
              </div>
            )}

            <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-md flex items-center justify-between">
              <div className="label-mini">Totale annuale stimato</div>
              <div className="font-display text-2xl font-semibold text-primary font-mono-num" data-testid="totale-costi">{fmtEuro(totale)}</div>
            </div>
          </section>

          <Separator />

          {/* Lavori & scadenze */}
          <section>
            <div className="label-mini mb-3">Scadenze</div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <Field label="Prossima antivegetativa">
                <Input type="date" value={f.scadenza_antivegetativa || ""} onChange={(e) => update("scadenza_antivegetativa", e.target.value)} data-testid="input-scadenza-antiveg" />
              </Field>
              <Field label="Prossima manutenzione motore">
                <Input type="date" value={f.scadenza_manutenzione || ""} onChange={(e) => update("scadenza_manutenzione", e.target.value)} data-testid="input-scadenza-motore" />
              </Field>
            </div>
            <Field label="Note generali">
              <Textarea rows={3} placeholder="Note generiche sul cliente o sulla barca…" value={f.note_lavori} onChange={(e) => update("note_lavori", e.target.value)} data-testid="input-note" />
            </Field>
          </section>

          <Separator />

          {/* Storico lavori strutturato */}
          <section>
            <LavoriSection clienteId={cliente?.id} />
          </section>

          {cliente?.id && (
            <>
              <Separator />
              <section>
                <div className="label-mini mb-3">Documenti</div>
                <Button variant="outline" asChild className="w-full" data-testid="btn-download-pdf">
                  <a href={`${API}/clienti/${cliente.id}/preventivo.pdf`} download target="_blank" rel="noreferrer">
                    <FileText className="w-4 h-4 mr-2" />
                    Scarica preventivo PDF
                  </a>
                </Button>
              </section>
            </>
          )}
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
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
        <Input
          type="number" step="0.01" min="0"
          disabled={disabled}
          value={value ?? 0}
          onChange={(e) => onChange(e.target.value)}
          className="pl-10 font-mono-num"
          data-testid={`input-${testId}`}
        />
      </div>
    </div>
  );
}

function BreakdownRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono-num">{new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(Number(value) || 0)}</span>
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange, testId }) {
  return (
    <div className="flex items-center justify-between gap-2 p-3 rounded-md border border-border bg-muted/30">
      <div className="min-w-0">
        <Label className="text-sm font-medium">{label}</Label>
        <p className="text-[11px] text-muted-foreground mt-0.5">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} data-testid={testId} />
    </div>
  );
}


