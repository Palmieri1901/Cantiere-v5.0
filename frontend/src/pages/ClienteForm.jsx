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
import { FileText, Plus, X, Wrench, Zap } from "lucide-react";

const empty = {
  nome: "", cognome: "", tipo_barca: "", lunghezza: "",
  tipo_sosta: "dentro",
  giorni_sosta_temporanea: 0, posto_barca: "",
  telefono: "", email: "",
  codice_fiscale: "", indirizzo: "", cellulare: "",
  pagato: false,
  potenza_motore: 0, litri_olio_motore: 3, litri_olio_piede: 1, numero_candele: 4, numero_termostati: 1,
  secondo_motore: false,
  potenza_motore_2: 0, litri_olio_motore_2: 3, litri_olio_piede_2: 1, numero_candele_2: 4, numero_termostati_2: 1,
  girante_2_attivo: true,
  antivegetativa_attiva: true, girante_attivo: true,
  scafo_sporco_attivo: false,
  copertura_attiva: false,
  lavaggio_inizio_attivo: true, lavaggio_fine_attivo: true,
  override_costi: false,
  costo_sosta: 0, costo_copertura: 0, costo_alaggio: 0,
  costo_varo: 0, costo_antivegetativa: 0, costo_manutenzione_motore: 0,
  costo_ricambi_totale: 0, costo_manodopera_motore: 0,
  costo_ricambi_motore_2_totale: 0, costo_manodopera_motore_2: 0,
  costo_lavaggio_inizio: 0, costo_lavaggio_fine: 0, costo_scafo_sporco: 0,
  lavorazioni_extra: [],
  note_lavori: "",
  scadenza_antivegetativa: "", scadenza_manutenzione: "",
};

export default function ClienteForm({ open, onOpenChange, cliente, onSaved, mode = "cliente" }) {
  const isPreventivo = mode === "preventivo";
  const [f, setF] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [ricambiDettaglio, setRicambiDettaglio] = useState(null);
  const [ricambi2Dettaglio, setRicambi2Dettaglio] = useState(null);
  const { year } = useYear();

  useEffect(() => {
    if (cliente) {
      setF({
        ...empty,
        ...cliente,
        posto_barca: cliente.posto_barca ?? "",
        scadenza_antivegetativa: cliente.scadenza_antivegetativa ?? "",
        scadenza_manutenzione: cliente.scadenza_manutenzione ?? "",
        lavorazioni_extra: Array.isArray(cliente.lavorazioni_extra) ? cliente.lavorazioni_extra : [],
      });
    } else {
      setF(empty);
    }
    setRicambiDettaglio(null);
    setRicambi2Dettaglio(null);
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
        secondo_motore: f.secondo_motore ? "true" : "false",
        potenza_motore_2: f.potenza_motore_2 || 0,
        litri_olio_motore_2: f.litri_olio_motore_2 || 0,
        numero_candele_2: f.numero_candele_2 || 0,
        numero_termostati_2: f.numero_termostati_2 || 0,
        girante_2_attivo: f.girante_2_attivo ? "true" : "false",
        scafo_sporco_attivo: f.scafo_sporco_attivo ? "true" : "false",
        copertura_attiva: f.copertura_attiva ? "true" : "false",
        litri_olio_piede: f.litri_olio_piede || 0,
        litri_olio_piede_2: f.litri_olio_piede_2 || 0,
        giorni_sosta_temporanea: f.giorni_sosta_temporanea || 0,
      });
      api.get(`/calcola-costi?${params}`)
        .then((r) => {
          const { ricambi_dettaglio, ricambi_2_dettaglio, ...rest } = r.data;
          setRicambiDettaglio(ricambi_dettaglio || null);
          setRicambi2Dettaglio(ricambi_2_dettaglio || null);
          setF((prev) => ({ ...prev, ...rest }));
        })
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [f.lunghezza, f.tipo_sosta, f.giorni_sosta_temporanea, f.potenza_motore, f.litri_olio_motore, f.litri_olio_piede, f.numero_candele, f.numero_termostati, f.antivegetativa_attiva, f.girante_attivo, f.lavaggio_inizio_attivo, f.lavaggio_fine_attivo, f.secondo_motore, f.potenza_motore_2, f.litri_olio_motore_2, f.litri_olio_piede_2, f.numero_candele_2, f.numero_termostati_2, f.girante_2_attivo, f.scafo_sporco_attivo, f.copertura_attiva, f.override_costi, open]);

  const update = (k, v) => setF((prev) => ({ ...prev, [k]: v }));

  const assegnaPostoAuto = async () => {
    try {
      const annoTarget = cliente?.anno || year;
      const params = new URLSearchParams({ anno: annoTarget });
      if (cliente?.id) params.set("escludi_cliente_id", cliente.id);
      const r = await api.get(`/posti-barca/next?${params}`);
      if (r.data?.posto) {
        update("posto_barca", r.data.posto);
        toast.success(`Posto #${String(r.data.posto).padStart(3, "0")} assegnato (${r.data.posti_liberi} posti liberi)`);
      } else {
        toast.error("Nessun posto libero disponibile per questo anno");
      }
    } catch {
      toast.error("Errore durante l'assegnazione automatica");
    }
  };

  // --- Lavorazioni extra helpers ---
  const MAX_EXTRA = 20;
  const totaleExtra = (Array.isArray(f.lavorazioni_extra) ? f.lavorazioni_extra : [])
    .reduce((s, it) => s + (Number(it?.prezzo) || 0), 0);

  const addExtra = () => {
    if ((f.lavorazioni_extra || []).length >= MAX_EXTRA) {
      toast.error(`Massimo ${MAX_EXTRA} lavorazioni extra`);
      return;
    }
    update("lavorazioni_extra", [...(f.lavorazioni_extra || []), { descrizione: "", prezzo: 0 }]);
  };
  const removeExtra = (idx) => {
    const list = [...(f.lavorazioni_extra || [])];
    list.splice(idx, 1);
    update("lavorazioni_extra", list);
  };
  const updateExtra = (idx, key, value) => {
    const list = [...(f.lavorazioni_extra || [])];
    list[idx] = { ...list[idx], [key]: key === "prezzo" ? value : String(value ?? "") };
    update("lavorazioni_extra", list);
  };

  const totale =
    (Number(f.costo_sosta) || 0) + (Number(f.costo_copertura) || 0) +
    (Number(f.costo_alaggio) || 0) + (Number(f.costo_varo) || 0) +
    (Number(f.costo_antivegetativa) || 0) + (Number(f.costo_manutenzione_motore) || 0) +
    (Number(f.costo_lavaggio_inizio) || 0) + (Number(f.costo_lavaggio_fine) || 0) +
    (Number(f.costo_scafo_sporco) || 0) + totaleExtra;

  const save = async () => {
    // Preventivo veloce: solo nome+cognome obbligatori
    if (isPreventivo) {
      if (!f.nome?.trim() || !f.cognome?.trim()) {
        toast.error("Inserisci almeno nome e cognome");
        return;
      }
    } else if (!f.nome || !f.cognome || !f.tipo_barca || !f.lunghezza) {
      toast.error("Compila nome, cognome, tipo barca e lunghezza");
      return;
    }
    setSaving(true);
    const payload = {
      ...f,
      anno: cliente?.anno || year,
      lunghezza: Number(f.lunghezza) || 0,
      potenza_motore: Number(f.potenza_motore) || 0,
      litri_olio_motore: Number(f.litri_olio_motore) || 0,
      numero_candele: Number(f.numero_candele) || 0,
      numero_termostati: Number(f.numero_termostati) || 0,
      antivegetativa_attiva: !!f.antivegetativa_attiva,
      girante_attivo: !!f.girante_attivo,
      lavaggio_inizio_attivo: !!f.lavaggio_inizio_attivo,
      lavaggio_fine_attivo: !!f.lavaggio_fine_attivo,
      secondo_motore: !!f.secondo_motore,
      potenza_motore_2: Number(f.potenza_motore_2) || 0,
      litri_olio_motore_2: Number(f.litri_olio_motore_2) || 0,
      numero_candele_2: Number(f.numero_candele_2) || 0,
      numero_termostati_2: Number(f.numero_termostati_2) || 0,
      girante_2_attivo: !!f.girante_2_attivo,
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
      lavorazioni_extra: (Array.isArray(f.lavorazioni_extra) ? f.lavorazioni_extra : [])
        .map((it) => ({
          descrizione: String(it?.descrizione ?? "").trim(),
          prezzo: Number(it?.prezzo) || 0,
        }))
        .filter((it) => it.descrizione || it.prezzo > 0),
      giorni_sosta_temporanea: Number(f.giorni_sosta_temporanea) || 0,
      litri_olio_piede: Number(f.litri_olio_piede) || 0,
      litri_olio_piede_2: Number(f.litri_olio_piede_2) || 0,
      scafo_sporco_attivo: !!f.scafo_sporco_attivo,
      copertura_attiva: !!f.copertura_attiva,
      scadenza_antivegetativa: f.scadenza_antivegetativa || null,
      scadenza_manutenzione: f.scadenza_manutenzione || null,
    };
    try {
      if (isPreventivo) {
        // Scarica il PDF senza salvare
        const res = await api.post("/preventivo/pdf", payload, { responseType: "blob" });
        const blob = new Blob([res.data], { type: "application/pdf" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `preventivo_${(f.cognome || "").trim()}_${(f.nome || "").trim()}.pdf`.replace(/\s+/g, "_");
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        toast.success("Preventivo PDF generato");
      } else if (cliente?.id) {
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
            {isPreventivo ? "Preventivo veloce" : (cliente ? "Modifica cliente" : "Nuovo cliente")}
          </SheetTitle>
          <SheetDescription>
            {isPreventivo
              ? "Compila almeno nome e cognome. Puoi aggiungere lunghezza, motore e servizi per un preventivo dettagliato. Il PDF viene generato senza salvare il cliente."
              : "Compila i dati del cliente. I costi vengono calcolati automaticamente in base alle tariffe."}
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
              <Field label="Codice fiscale">
                <Input value={f.codice_fiscale} onChange={(e) => update("codice_fiscale", e.target.value.toUpperCase())} maxLength={16} className="uppercase font-mono-num" data-testid="input-codice-fiscale" />
              </Field>
              <Field label="Indirizzo">
                <Input value={f.indirizzo} onChange={(e) => update("indirizzo", e.target.value)} placeholder="Via, città, CAP" data-testid="input-indirizzo" />
              </Field>
              <Field label="Telefono">
                <Input value={f.telefono} onChange={(e) => update("telefono", e.target.value)} data-testid="input-telefono" />
              </Field>
              <Field label="Cellulare">
                <Input value={f.cellulare} onChange={(e) => update("cellulare", e.target.value)} data-testid="input-cellulare" />
              </Field>
              <div className="col-span-2">
                <Field label="Email">
                  <Input type="email" value={f.email} onChange={(e) => update("email", e.target.value)} data-testid="input-email" />
                </Field>
              </div>
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
                    <SelectItem value="fuori">Su piazzale (fuori)</SelectItem>
                    <SelectItem value="fuori_sede">Fuori sede</SelectItem>
                    <SelectItem value="temporanea">Temporanea (a giorni)</SelectItem>
                  </SelectContent>
                </Select>
                {f.tipo_sosta === "temporanea" && (
                  <div className="mt-2" data-testid="wrap-giorni-temporanea">
                    <Label className="text-xs text-muted-foreground">N° giorni</Label>
                    <Input
                      type="number" min="0" step="1"
                      placeholder="es. 15"
                      value={f.giorni_sosta_temporanea}
                      onChange={(e) => update("giorni_sosta_temporanea", e.target.value)}
                      className="mt-1 font-mono-num"
                      data-testid="input-giorni-temporanea"
                    />
                  </div>
                )}
              </Field>
              <Field label="Posto barca (1-200)">
                <div className="flex gap-2">
                  <Input type="number" min="1" max="200" placeholder="Assegna dopo…" value={f.posto_barca} onChange={(e) => update("posto_barca", e.target.value)} data-testid="input-posto-barca" />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={assegnaPostoAuto}
                    className="shrink-0"
                    title="Assegna primo posto libero"
                    data-testid="btn-posto-auto"
                  >
                    <Zap className="w-4 h-4" />
                  </Button>
                </div>
              </Field>
            </div>
          </section>

          <Separator />

          {/* Motore */}
          <section>
            <div className="label-mini mb-3">{f.secondo_motore ? "1° Motore" : "Motore"}</div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Field label="Cavalli (HP)">
                <Input type="number" min="0" step="1" value={f.potenza_motore} onChange={(e) => update("potenza_motore", e.target.value)} data-testid="input-potenza-motore" />
              </Field>
              <Field label="Litri olio motore">
                <Input type="number" min="0" step="0.1" value={f.litri_olio_motore} onChange={(e) => update("litri_olio_motore", e.target.value)} data-testid="input-litri-olio" />
              </Field>
              <Field label="Litri olio piede">
                <Input type="number" min="0" step="0.1" value={f.litri_olio_piede} onChange={(e) => update("litri_olio_piede", e.target.value)} data-testid="input-litri-olio-piede" />
              </Field>
              <Field label="N° candele">
                <Input type="number" min="0" step="1" value={f.numero_candele} onChange={(e) => update("numero_candele", e.target.value)} data-testid="input-numero-candele" />
              </Field>
              <Field label="N° termostati">
                <Input type="number" min="0" step="1" value={f.numero_termostati} onChange={(e) => update("numero_termostati", e.target.value)} data-testid="input-numero-termostati" />
              </Field>
            </div>
            <div className="text-[11px] text-muted-foreground mt-2">
              Fasce manodopera: 2-15 HP · 16-40 HP · 41-150 HP · &gt;150 HP. Olio motore calcolato al litro. I ricambi si moltiplicano per il numero indicato.
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
                label="Scafo sporco"
                description="Applica la maggiorazione scafo sporco"
                checked={!!f.scafo_sporco_attivo}
                onChange={(v) => update("scafo_sporco_attivo", v)}
                testId="switch-scafo-sporco"
              />
              <ToggleRow
                label="Copertura"
                description={f.tipo_sosta === "dentro" ? "Non applicabile con sosta al coperto" : "Applica il costo copertura (€ / metro)"}
                checked={!!f.copertura_attiva}
                onChange={(v) => update("copertura_attiva", v)}
                testId="switch-copertura"
                disabled={f.tipo_sosta === "dentro"}
              />
              <ToggleRow
                label={f.secondo_motore ? "Girante 1° motore" : "Sostituzione girante"}
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
            {!f.antivegetativa_attiva && !f.scafo_sporco_attivo && (
              <div className="mt-2 text-[11px] text-muted-foreground bg-muted/40 border border-border rounded-md p-2" data-testid="info-no-antiveg">
                Antivegetativa disattivata. Attiva "Scafo sporco" se serve applicare la maggiorazione.
              </div>
            )}

            {/* Secondo motore */}
            <div className="mt-4 p-4 rounded-md border border-border bg-muted/20">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <Label className="text-sm font-medium">Secondo motore</Label>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Attiva se la barca ha un secondo motore. I ricambi vengono calcolati separatamente.
                  </p>
                </div>
                <Switch checked={!!f.secondo_motore} onCheckedChange={(v) => update("secondo_motore", v)} data-testid="switch-secondo-motore" />
              </div>
              {f.secondo_motore && (
                <div className="pt-3 border-t border-border/60 space-y-3">
                  <div className="label-mini">2° Motore</div>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <Field label="Cavalli 2° motore">
                      <Input type="number" min="0" step="1" value={f.potenza_motore_2} onChange={(e) => update("potenza_motore_2", e.target.value)} data-testid="input-potenza-motore-2" />
                    </Field>
                    <Field label="Litri olio 2°">
                      <Input type="number" min="0" step="0.1" value={f.litri_olio_motore_2} onChange={(e) => update("litri_olio_motore_2", e.target.value)} data-testid="input-litri-olio-2" />
                    </Field>
                    <Field label="Lt olio piede 2°">
                      <Input type="number" min="0" step="0.1" value={f.litri_olio_piede_2} onChange={(e) => update("litri_olio_piede_2", e.target.value)} data-testid="input-litri-olio-piede-2" />
                    </Field>
                    <Field label="N° candele 2°">
                      <Input type="number" min="0" step="1" value={f.numero_candele_2} onChange={(e) => update("numero_candele_2", e.target.value)} data-testid="input-numero-candele-2" />
                    </Field>
                    <Field label="N° termostati 2°">
                      <Input type="number" min="0" step="1" value={f.numero_termostati_2} onChange={(e) => update("numero_termostati_2", e.target.value)} data-testid="input-numero-termostati-2" />
                    </Field>
                  </div>
                  <ToggleRow
                    label="Girante 2° motore"
                    description="Includi ricambio girante per il 2° motore"
                    checked={!!f.girante_2_attivo}
                    onChange={(v) => update("girante_2_attivo", v)}
                    testId="switch-girante-2"
                  />
                </div>
              )}
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
                <div className="label-mini mb-2">{f.secondo_motore ? "Dettaglio 1° motore" : "Dettaglio motore"}</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <BreakdownRow label="Manodopera" value={f.costo_manodopera_motore} />
                  <BreakdownRow label="Girante" value={ricambiDettaglio.girante} />
                  <BreakdownRow label={`Olio motore (${f.litri_olio_motore || 0}L)`} value={ricambiDettaglio.olio_motore} />
                  <BreakdownRow label="Filtro olio" value={ricambiDettaglio.filtro_olio} />
                  <BreakdownRow label={`Candele (${f.numero_candele || 0})`} value={ricambiDettaglio.candele} />
                  <BreakdownRow label={`Termostati (${f.numero_termostati || 0})`} value={ricambiDettaglio.termostati} />
                  <BreakdownRow label={`Olio piede (${f.litri_olio_piede || 0}L)`} value={ricambiDettaglio.olio_piede} />
                  <BreakdownRow label="Anodi interni" value={ricambiDettaglio.anodi_interni} />
                  <BreakdownRow label="Anodi esterni" value={ricambiDettaglio.anodi_esterni} />
                  <BreakdownRow label="Ingrassaggio" value={ricambiDettaglio.ingrassaggio} />
                </div>
                <div className="flex justify-between mt-2 pt-2 border-t border-border/60 text-xs">
                  <span className="font-semibold">Subtotale 1° motore</span>
                  <span className="font-mono-num font-semibold text-primary">
                    {fmtEuro((Number(f.costo_manodopera_motore) || 0) + (Number(f.costo_ricambi_totale) || 0))}
                  </span>
                </div>
              </div>
            )}

            {/* Dettaglio 2° motore */}
            {!f.override_costi && f.secondo_motore && ricambi2Dettaglio && Number(f.potenza_motore_2) > 0 && (
              <div className="mt-3 p-3 bg-muted/40 border border-border rounded-md" data-testid="ricambi-breakdown-2">
                <div className="label-mini mb-2">Dettaglio 2° motore</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <BreakdownRow label="Manodopera" value={f.costo_manodopera_motore_2} />
                  <BreakdownRow label="Girante" value={ricambi2Dettaglio.girante} />
                  <BreakdownRow label={`Olio motore (${f.litri_olio_motore_2 || 0}L)`} value={ricambi2Dettaglio.olio_motore} />
                  <BreakdownRow label="Filtro olio" value={ricambi2Dettaglio.filtro_olio} />
                  <BreakdownRow label={`Candele (${f.numero_candele_2 || 0})`} value={ricambi2Dettaglio.candele} />
                  <BreakdownRow label={`Termostati (${f.numero_termostati_2 || 0})`} value={ricambi2Dettaglio.termostati} />
                  <BreakdownRow label={`Olio piede (${f.litri_olio_piede_2 || 0}L)`} value={ricambi2Dettaglio.olio_piede} />
                  <BreakdownRow label="Anodi interni" value={ricambi2Dettaglio.anodi_interni} />
                  <BreakdownRow label="Anodi esterni" value={ricambi2Dettaglio.anodi_esterni} />
                  <BreakdownRow label="Ingrassaggio" value={ricambi2Dettaglio.ingrassaggio} />
                </div>
                <div className="flex justify-between mt-2 pt-2 border-t border-border/60 text-xs">
                  <span className="font-semibold">Subtotale 2° motore</span>
                  <span className="font-mono-num font-semibold text-primary">
                    {fmtEuro((Number(f.costo_manodopera_motore_2) || 0) + (Number(f.costo_ricambi_motore_2_totale) || 0))}
                  </span>
                </div>
              </div>
            )}

            <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-md flex items-center justify-between">
              <div className="label-mini">Totale annuale stimato</div>
              <div className="font-display text-2xl font-semibold text-primary font-mono-num" data-testid="totale-costi">{fmtEuro(totale)}</div>
            </div>
          </section>

          <Separator />

          {/* Lavorazioni extra */}
          <section data-testid="section-lavorazioni-extra">
            <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
              <div>
                <div className="flex items-center gap-1.5 label-mini mb-0.5">
                  <Wrench className="w-3 h-3" /> Lavorazioni extra
                </div>
                <p className="text-xs text-muted-foreground">
                  Aggiungi lavorazioni personalizzate con prezzo (max {MAX_EXTRA}). Sono incluse nel totale e nel PDF preventivo.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addExtra}
                disabled={(f.lavorazioni_extra || []).length >= MAX_EXTRA}
                data-testid="btn-add-extra"
              >
                <Plus className="w-4 h-4 mr-1" /> Aggiungi voce
              </Button>
            </div>

            {(f.lavorazioni_extra || []).length === 0 ? (
              <div className="text-xs text-muted-foreground bg-muted/40 rounded-md p-3 border border-dashed border-border text-center" data-testid="extra-empty">
                Nessuna lavorazione extra. Clicca su "Aggiungi voce" per crearne una.
              </div>
            ) : (
              <div className="space-y-2" data-testid="extra-list">
                {(f.lavorazioni_extra || []).map((it, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-center" data-testid={`extra-row-${idx}`}>
                    <div className="col-span-7">
                      <Input
                        placeholder="Descrizione (es. Riparazione elica)"
                        value={it?.descrizione ?? ""}
                        onChange={(e) => updateExtra(idx, "descrizione", e.target.value)}
                        data-testid={`extra-desc-${idx}`}
                      />
                    </div>
                    <div className="col-span-4 relative">
                      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
                      <Input
                        type="number" step="0.01" min="0"
                        placeholder="0,00"
                        value={it?.prezzo ?? ""}
                        onChange={(e) => updateExtra(idx, "prezzo", e.target.value)}
                        className="pl-10 font-mono-num"
                        data-testid={`extra-prezzo-${idx}`}
                      />
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <Button
                        type="button" size="icon" variant="ghost"
                        onClick={() => removeExtra(idx)}
                        data-testid={`extra-remove-${idx}`}
                        title="Rimuovi voce"
                      >
                        <X className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {(f.lavorazioni_extra || []).length > 0 && (
              <div className="mt-3 flex items-center justify-between text-sm bg-muted/40 border border-border rounded-md px-3 py-2">
                <span className="text-muted-foreground">
                  {(f.lavorazioni_extra || []).length} / {MAX_EXTRA} voci
                </span>
                <span className="font-semibold" data-testid="extra-totale">
                  Subtotale extra: <span className="font-mono-num text-primary">{fmtEuro(totaleExtra)}</span>
                </span>
              </div>
            )}
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
            {isPreventivo
              ? (saving ? "Generazione…" : (<><FileText className="w-4 h-4 mr-2" /> Scarica preventivo PDF</>))
              : (saving ? "Salvataggio…" : "Salva cliente")}
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

function ToggleRow({ label, description, checked, onChange, testId, disabled }) {
  return (
    <div className={`flex items-center justify-between gap-2 p-3 rounded-md border border-border bg-muted/30 ${disabled ? "opacity-50" : ""}`}>
      <div className="min-w-0">
        <Label className="text-sm font-medium">{label}</Label>
        <p className="text-[11px] text-muted-foreground mt-0.5">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} disabled={disabled} data-testid={testId} />
    </div>
  );
}


