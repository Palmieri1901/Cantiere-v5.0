import { fmtEuro } from "@/lib/api";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { API } from "@/lib/api";
import { FileText, Anchor, Wrench, Waves, Package } from "lucide-react";

const SOSTA_LABEL = {
  dentro: "Al coperto",
  fuori: "Su piazzale (fuori)",
  fuori_sede: "Fuori sede",
  temporanea: "Temporanea",
};

function Row({ label, value, muted = false }) {
  const v = Number(value) || 0;
  if (v === 0 && !muted) return null;
  return (
    <div className="flex justify-between items-baseline py-1.5 text-sm">
      <span className={muted ? "text-muted-foreground" : "text-foreground"}>{label}</span>
      <span className="font-mono-num font-medium">{fmtEuro(v)}</span>
    </div>
  );
}

function SectionTitle({ icon: Icon, children }) {
  return (
    <div className="flex items-center gap-2 label-mini mt-4 mb-1">
      <Icon className="w-3.5 h-3.5" /> {children}
    </div>
  );
}

export default function ClienteDettaglio({ open, onOpenChange, cliente }) {
  if (!cliente) return null;
  const c = cliente;
  const lav_extra = Array.isArray(c.lavorazioni_extra) ? c.lavorazioni_extra : [];
  const tot_extra = lav_extra.reduce((s, it) => s + (Number(it?.prezzo) || 0), 0);
  const keys = [
    "costo_sosta", "costo_movimentazione", "costo_taccaggio", "costo_copertura",
    "costo_alaggio", "costo_varo", "costo_antivegetativa", "costo_scafo_sporco",
    "costo_lavaggio_inizio", "costo_lavaggio_fine", "costo_manutenzione_motore",
  ];
  const totale = keys.reduce((s, k) => s + (Number(c[k]) || 0), 0) + tot_extra;

  const dest = c.destinazione_alaggio_varo || "marina_di_campo";
  const destNome = (c.destinazione_altra_nome || "").trim();
  const mov = Number(c.numero_movimenti || 1);
  const suffixMov = mov > 1 ? ` × ${mov} mov.` : "";
  const labelAlaggio = dest === "altra" && destNome
    ? `Alaggio (${destNome})${suffixMov}`
    : `Alaggio${suffixMov}`;
  const labelVaro = dest === "altra" && destNome
    ? `Varo (${destNome})${suffixMov}`
    : `Varo${suffixMov}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="cliente-dettaglio">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl flex items-center gap-2">
            <Anchor className="w-5 h-5 text-primary" />
            {c.cognome} {c.nome}
          </DialogTitle>
          <DialogDescription>
            Conteggio dettagliato dei costi annuali. Anno <b>{c.anno}</b>.
          </DialogDescription>
        </DialogHeader>

        {/* Info sintesi */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="p-3 rounded-md bg-muted/40 border border-border">
            <div className="label-mini mb-1">Imbarcazione</div>
            <div className="text-sm"><b>{c.tipo_barca || "—"}</b></div>
            <div className="text-xs text-muted-foreground">Lunghezza: {c.lunghezza} m</div>
            {c.posto_barca && (
              <div className="text-xs text-muted-foreground">Posto #{String(c.posto_barca).padStart(3, "0")}</div>
            )}
          </div>
          <div className="p-3 rounded-md bg-muted/40 border border-border">
            <div className="label-mini mb-1">Sosta</div>
            <Badge variant="outline" className="text-xs">{SOSTA_LABEL[c.tipo_sosta] || c.tipo_sosta}</Badge>
            {c.tipo_sosta === "temporanea" && (
              <div className="text-xs text-muted-foreground mt-1">Giorni: {c.giorni_sosta_temporanea || 0}</div>
            )}
            {c.pagato && <div className="text-xs text-emerald-700 mt-1">Pagato {c.data_pagamento ? `il ${c.data_pagamento}` : ""}</div>}
            {!c.pagato && <div className="text-xs text-amber-700 mt-1">Non pagato</div>}
          </div>
        </div>

        <Separator className="my-4" />

        {/* Costi sosta / trattamenti */}
        <SectionTitle icon={Waves}>Sosta & trattamenti</SectionTitle>
        <Row label="Costo sosta" value={c.costo_sosta} />
        <Row label="Movimentazione (fuori sede)" value={c.costo_movimentazione} />
        <Row label="Taccaggio (fuori sede)" value={c.costo_taccaggio} />
        <Row label="Copertura" value={c.costo_copertura} />
        <Row label="Antivegetativa" value={c.costo_antivegetativa} />
        <Row label="Magg. scafo sporco" value={c.costo_scafo_sporco} />
        <Row label="Lavaggio inizio stagione" value={c.costo_lavaggio_inizio} />
        <Row label="Lavaggio fine stagione" value={c.costo_lavaggio_fine} />

        {/* Alaggio & Varo */}
        {(c.alaggio_varo_attivo || Number(c.costo_alaggio) > 0 || Number(c.costo_varo) > 0) && (
          <>
            <SectionTitle icon={Anchor}>Alaggio & Varo</SectionTitle>
            <Row label={labelAlaggio} value={c.costo_alaggio} />
            <Row label={labelVaro} value={c.costo_varo} />
          </>
        )}

        {/* Motore */}
        {Number(c.costo_manutenzione_motore) > 0 && (
          <>
            <SectionTitle icon={Wrench}>
              Manutenzione motore {c.potenza_motore ? `· ${c.potenza_motore} HP` : ""}
              {c.secondo_motore && c.potenza_motore_2 ? ` + ${c.potenza_motore_2} HP` : ""}
            </SectionTitle>
            <Row label="Manodopera 1° motore" value={c.costo_manodopera_motore} muted />
            <Row label="Ricambi 1° motore" value={c.costo_ricambi_totale} muted />
            {c.secondo_motore && (
              <>
                <Row label="Manodopera 2° motore" value={c.costo_manodopera_motore_2} muted />
                <Row label="Ricambi 2° motore" value={c.costo_ricambi_motore_2_totale} muted />
              </>
            )}
            <div className="flex justify-between items-baseline py-1.5 pt-2 border-t border-border/40 text-sm">
              <span className="font-medium">Totale manutenzione motore</span>
              <span className="font-mono-num font-semibold text-primary">{fmtEuro(Number(c.costo_manutenzione_motore) || 0)}</span>
            </div>
          </>
        )}

        {/* Lavorazioni extra */}
        {lav_extra.length > 0 && tot_extra > 0 && (
          <>
            <SectionTitle icon={Package}>Lavorazioni extra</SectionTitle>
            {lav_extra.filter((it) => (Number(it?.prezzo) || 0) > 0 || (it?.descrizione || "").trim()).map((it, i) => (
              <div key={i} className="flex justify-between items-baseline py-1 text-sm">
                <span className="text-foreground truncate pr-3">{it.descrizione || <span className="text-muted-foreground italic">Voce senza descrizione</span>}</span>
                <span className="font-mono-num font-medium shrink-0">{fmtEuro(Number(it.prezzo) || 0)}</span>
              </div>
            ))}
            <div className="flex justify-between items-baseline py-1.5 pt-2 border-t border-border/40 text-sm">
              <span className="font-medium">Totale lavorazioni extra</span>
              <span className="font-mono-num font-semibold text-primary">{fmtEuro(tot_extra)}</span>
            </div>
          </>
        )}

        <Separator className="my-4" />

        {/* Totale finale */}
        <div className="flex justify-between items-baseline p-4 rounded-md bg-primary text-primary-foreground" data-testid="dettaglio-totale">
          <span className="font-display text-lg">TOTALE ANNUALE</span>
          <span className="font-mono-num text-2xl font-semibold">{fmtEuro(totale)}</span>
        </div>

        <DialogFooter className="mt-4 flex-col sm:flex-row gap-2">
          <Button variant="outline" asChild data-testid="btn-dettaglio-pdf">
            <a href={`${API}/clienti/${c.id}/preventivo.pdf`} download target="_blank" rel="noreferrer">
              <FileText className="w-4 h-4 mr-2" /> Scarica preventivo PDF
            </a>
          </Button>
          <Button onClick={() => onOpenChange(false)} data-testid="btn-dettaglio-chiudi">Chiudi</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
