import { useEffect, useMemo, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { Plus, Search, Pencil, Trash2, FileSpreadsheet, FileDown, FileText, Eye, CheckCircle2, XCircle, AlertCircle, History } from "lucide-react";
import { toast } from "sonner";
import ClienteForm from "@/pages/ClienteForm";
import ClienteDettaglio from "@/pages/ClienteDettaglio";
import { API } from "@/lib/api";
import { useYear } from "@/lib/year";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";


export default function Clienti() {
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [tipoSostaFilter, setTipoSostaFilter] = useState("all");
  const [pagamentoFilter, setPagamentoFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [dettaglio, setDettaglio] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [openStorico, setOpenStorico] = useState(false);
  const [nominativi, setNominativi] = useState([]);
  const [storicoSel, setStoricoSel] = useState("");
  const { year } = useYear();

  const load = () => {
    setLoading(true);
    api.get(`/clienti?anno=${year}`).then((r) => {
      setClienti(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [year]);

  const filtered = useMemo(() => {
    const list = clienti.filter((c) => {
      if (tipoSostaFilter !== "all" && c.tipo_sosta !== tipoSostaFilter) return false;
      if (pagamentoFilter === "pagati" && !c.pagato) return false;
      if (pagamentoFilter === "non_pagati" && c.pagato) return false;
      if (!q) return true;
      const s = q.toLowerCase();
      return (
        c.nome?.toLowerCase().includes(s) ||
        c.cognome?.toLowerCase().includes(s) ||
        c.tipo_barca?.toLowerCase().includes(s) ||
        String(c.posto_barca || "").includes(s)
      );
    });
    // Ordina alfabeticamente per cognome (case + accent insensitive), poi per nome
    return [...list].sort((a, b) => {
      const cog = (a.cognome || "").localeCompare(b.cognome || "", "it", { sensitivity: "base" });
      if (cog !== 0) return cog;
      return (a.nome || "").localeCompare(b.nome || "", "it", { sensitivity: "base" });
    });
  }, [clienti, q, tipoSostaFilter, pagamentoFilter]);

  const totale = (c) => {
    const base = (c.costo_sosta || 0) + (c.costo_copertura || 0) + (c.costo_alaggio || 0) +
      (c.costo_varo || 0) + (c.costo_antivegetativa || 0) + (c.costo_manutenzione_motore || 0) +
      (c.costo_lavaggio_inizio || 0) + (c.costo_lavaggio_fine || 0) + (c.costo_scafo_sporco || 0) +
      (c.costo_movimentazione || 0) + (c.costo_taccaggio || 0);
    const extra = (Array.isArray(c.lavorazioni_extra) ? c.lavorazioni_extra : [])
      .reduce((s, it) => s + (Number(it?.prezzo) || 0), 0);
    return base + extra;
  };

  // Riepilogo pagamenti su TUTTI i clienti dell'anno (non solo filtrati)
  const riepilogoPagamenti = useMemo(() => {
    let daIncassare = 0, incassati = 0, nPagati = 0, nNonPagati = 0;
    clienti.forEach((c) => {
      const t = (c.costo_sosta || 0) + (c.costo_copertura || 0) + (c.costo_alaggio || 0) +
        (c.costo_varo || 0) + (c.costo_antivegetativa || 0) + (c.costo_manutenzione_motore || 0) +
        (c.costo_lavaggio_inizio || 0) + (c.costo_lavaggio_fine || 0) + (c.costo_scafo_sporco || 0) +
        (c.costo_movimentazione || 0) + (c.costo_taccaggio || 0) +
        (Array.isArray(c.lavorazioni_extra) ? c.lavorazioni_extra : []).reduce((s, it) => s + (Number(it?.prezzo) || 0), 0);
      if (c.pagato) { incassati += t; nPagati += 1; }
      else { daIncassare += t; nNonPagati += 1; }
    });
    return { daIncassare, incassati, nPagati, nNonPagati };
  }, [clienti]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/clienti/${deleteTarget.id}`);
      toast.success("Cliente eliminato");
      setDeleteTarget(null);
      load();
    } catch {
      toast.error("Errore nell'eliminazione");
    }
  };

  const togglePagato = async (c) => {
    try {
      const nuovoStato = !c.pagato;
      const payload = {
        nome: c.nome, cognome: c.cognome, tipo_barca: c.tipo_barca,
        lunghezza: c.lunghezza, tipo_sosta: c.tipo_sosta,
        pagato: nuovoStato,
        data_pagamento: nuovoStato ? new Date().toISOString().slice(0, 10) : null,
      };
      await api.put(`/clienti/${c.id}`, payload);
      toast.success(nuovoStato ? "Segnato come pagato" : "Segnato come non pagato");
      load();
    } catch {
      toast.error("Errore aggiornamento pagamento");
    }
  };

  return (
    <div className="p-6 md:p-10 max-w-[1400px]" data-testid="clienti-page">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <div className="label-mini mb-2">Anagrafica</div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Clienti</h1>
          <p className="text-muted-foreground mt-1">{clienti.length} clienti registrati</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild data-testid="btn-export-csv">
            <a href={`${API}/export/clienti.csv?anno=${year}`} download>
              <FileDown className="w-4 h-4 mr-2" /> CSV
            </a>
          </Button>
          <Button variant="outline" asChild data-testid="btn-export-xlsx">
            <a href={`${API}/export/clienti.xlsx?anno=${year}`} download>
              <FileSpreadsheet className="w-4 h-4 mr-2" /> Excel
            </a>
          </Button>
          <Button
            variant="outline"
            data-testid="btn-storico-cliente"
            onClick={() => {
              api.get("/clienti-nominativi").then((r) => setNominativi(r.data || []));
              setStoricoSel("");
              setOpenStorico(true);
            }}
          >
            <History className="w-4 h-4 mr-2" /> Storico cliente
          </Button>
          <Button
            onClick={() => { setEditing(null); setFormOpen(true); }}
            data-testid="btn-nuovo-cliente"
            className="bg-primary hover:bg-primary/90"
          >
            <Plus className="w-4 h-4 mr-2" /> Nuovo cliente
          </Button>
        </div>
      </div>

      {/* Riepilogo pagamenti */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4" data-testid="riepilogo-pagamenti">
        <button
          type="button"
          onClick={() => setPagamentoFilter("all")}
          data-testid="kpi-tutti"
          className={`text-left p-4 rounded-lg border transition-all ${pagamentoFilter === "all" ? "border-primary bg-primary/5 ring-2 ring-primary/30" : "border-border bg-card hover:border-primary/30"}`}
        >
          <div className="flex items-center gap-1.5 label-mini mb-1"><Eye className="w-3.5 h-3.5" /> Tutti</div>
          <div className="font-display text-2xl font-semibold">{clienti.length}</div>
          <div className="text-xs text-muted-foreground mt-0.5">Totale clienti anno {year}</div>
        </button>
        <button
          type="button"
          onClick={() => setPagamentoFilter("non_pagati")}
          data-testid="kpi-non-pagati"
          className={`text-left p-4 rounded-lg border transition-all ${pagamentoFilter === "non_pagati" ? "border-destructive bg-destructive/5 ring-2 ring-destructive/30" : "border-border bg-card hover:border-destructive/30"}`}
        >
          <div className="flex items-center gap-1.5 label-mini mb-1 text-destructive"><AlertCircle className="w-3.5 h-3.5" /> Da incassare</div>
          <div className="font-display text-2xl font-semibold text-destructive font-mono-num">{fmtEuro(riepilogoPagamenti.daIncassare)}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{riepilogoPagamenti.nNonPagati} clienti non hanno pagato</div>
        </button>
        <button
          type="button"
          onClick={() => setPagamentoFilter("pagati")}
          data-testid="kpi-pagati"
          className={`text-left p-4 rounded-lg border transition-all ${pagamentoFilter === "pagati" ? "border-emerald-500 bg-emerald-50/50 ring-2 ring-emerald-300/40" : "border-border bg-card hover:border-emerald-400/40"}`}
        >
          <div className="flex items-center gap-1.5 label-mini mb-1 text-emerald-700"><CheckCircle2 className="w-3.5 h-3.5" /> Incassato</div>
          <div className="font-display text-2xl font-semibold text-emerald-700 font-mono-num">{fmtEuro(riepilogoPagamenti.incassati)}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{riepilogoPagamenti.nPagati} clienti hanno saldato</div>
        </button>
      </div>

      <Card className="p-4 mb-4">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Cerca nome, cognome, tipo barca, posto…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="pl-9"
              data-testid="input-search"
            />
          </div>
          <Select value={tipoSostaFilter} onValueChange={setTipoSostaFilter}>
            <SelectTrigger className="w-[200px]" data-testid="filter-tipo-sosta">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tutti i tipi</SelectItem>
              <SelectItem value="dentro">Sosta al coperto</SelectItem>
              <SelectItem value="fuori">Su piazzale</SelectItem>
              <SelectItem value="fuori_sede">Fuori sede</SelectItem>
              <SelectItem value="temporanea">Temporanea</SelectItem>
            </SelectContent>
          </Select>
          <Select value={pagamentoFilter} onValueChange={setPagamentoFilter}>
            <SelectTrigger className="w-[180px]" data-testid="filter-pagamento">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tutti i pagamenti</SelectItem>
              <SelectItem value="non_pagati">Solo non pagati</SelectItem>
              <SelectItem value="pagati">Solo pagati</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead className="w-16">Posto</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Barca</TableHead>
              <TableHead className="text-right">Lungh.</TableHead>
              <TableHead>Sosta</TableHead>
              <TableHead>Pagamento</TableHead>
              <TableHead className="text-right">Totale</TableHead>
              <TableHead className="w-40 text-right">Azioni</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={8} className="py-8 text-center text-muted-foreground">Caricamento…</TableCell></TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-16 text-center">
                  <div className="text-muted-foreground mb-3">Nessun cliente trovato.</div>
                  <Button variant="outline" onClick={() => { setEditing(null); setFormOpen(true); }} data-testid="btn-nuovo-cliente-empty">
                    <Plus className="w-4 h-4 mr-2" /> Aggiungi il primo cliente
                  </Button>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((c) => (
                <TableRow key={c.id} className="hover:bg-muted/40" data-testid={`row-cliente-${c.id}`}>
                  <TableCell className="font-mono-num font-semibold">
                    {c.posto_barca ? `#${String(c.posto_barca).padStart(3, "0")}` : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">{c.cognome} {c.nome}</div>
                    {c.telefono && <div className="text-xs text-muted-foreground">{c.telefono}</div>}
                  </TableCell>
                  <TableCell>{c.tipo_barca}</TableCell>
                  <TableCell className="text-right font-mono-num">{c.lunghezza} m</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={c.tipo_sosta === "dentro"
                        ? "border-primary/50 text-primary bg-primary/5"
                        : c.tipo_sosta === "fuori_sede"
                        ? "border-chart-3/50 text-chart-3 bg-chart-3/5"
                        : "border-chart-2/50"}
                    >
                      {c.tipo_sosta === "dentro" ? "Coperto" : c.tipo_sosta === "fuori_sede" ? "Fuori sede" : c.tipo_sosta === "temporanea" ? "Piazzale (temp.)" : "Su piazzale"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {c.pagato ? (
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 hover:bg-emerald-100" data-testid={`badge-pagato-${c.id}`}>
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Pagato
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-destructive/40 text-destructive bg-destructive/5" data-testid={`badge-non-pagato-${c.id}`}>
                        <XCircle className="w-3 h-3 mr-1" /> Non pagato
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono-num font-semibold">{fmtEuro(totale(c))}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="icon" variant="ghost"
                        onClick={() => togglePagato(c)}
                        data-testid={`btn-toggle-pagato-${c.id}`}
                        title={c.pagato ? "Segna come NON pagato" : "Segna come pagato"}
                      >
                        {c.pagato ? <XCircle className="w-4 h-4 text-destructive" /> : <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => setDettaglio(c)} data-testid={`btn-dettaglio-${c.id}`} title="Vedi conteggio dettagliato">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button size="icon" variant="ghost" asChild data-testid={`btn-pdf-${c.id}`} title="Scarica preventivo PDF">
                        <a href={`${API}/clienti/${c.id}/preventivo.pdf`} download target="_blank" rel="noreferrer">
                          <FileText className="w-4 h-4" />
                        </a>
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => { setEditing(c); setFormOpen(true); }} data-testid={`btn-edit-${c.id}`}>
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => setDeleteTarget(c)} data-testid={`btn-delete-${c.id}`}>
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      <ClienteForm
        open={formOpen}
        onOpenChange={setFormOpen}
        cliente={editing}
        onSaved={load}
      />

      <ClienteDettaglio
        open={!!dettaglio}
        onOpenChange={(o) => !o && setDettaglio(null)}
        cliente={dettaglio}
      />

      <Dialog open={openStorico} onOpenChange={setOpenStorico}>
        <DialogContent className="max-w-md" data-testid="dialog-storico-cliente">
          <DialogHeader>
            <DialogTitle className="font-display flex items-center gap-2">
              <History className="w-5 h-5 text-primary" /> Storico cliente
            </DialogTitle>
            <DialogDescription>
              Seleziona il cliente per generare un report PDF A4 diviso per anni.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="label-mini block mb-2">Nome cliente</label>
            <Select value={storicoSel} onValueChange={setStoricoSel}>
              <SelectTrigger data-testid="select-storico-cliente" className="w-full">
                <SelectValue placeholder="Seleziona un cliente…" />
              </SelectTrigger>
              <SelectContent className="max-h-[320px]">
                {nominativi.length === 0 && (
                  <div className="px-3 py-4 text-sm text-muted-foreground">Nessun cliente registrato</div>
                )}
                {nominativi.map((n) => {
                  const key = `${n.cognome}|${n.nome}`;
                  const anniStr = (n.anni && n.anni.length) ? n.anni.join(", ") : "—";
                  return (
                    <SelectItem key={key} value={key}>
                      <span>{n.cognome} {n.nome}</span>
                      <span className="text-xs text-muted-foreground ml-2">· {anniStr}</span>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            {storicoSel && (
              <p className="text-[11px] text-muted-foreground mt-2">
                Il PDF includerà una sezione per ogni anno con tutti i costi e il totale generale.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenStorico(false)} data-testid="btn-storico-annulla">Annulla</Button>
            <Button
              asChild={!!storicoSel}
              disabled={!storicoSel}
              className="bg-primary hover:bg-primary/90"
              data-testid="btn-storico-scarica"
              onClick={() => { if (storicoSel) { setOpenStorico(false); toast.success("Storico in download"); } }}
            >
              {storicoSel ? (
                <a
                  href={`${API}/clienti-storico.pdf?cognome=${encodeURIComponent(storicoSel.split("|")[0])}&nome=${encodeURIComponent(storicoSel.split("|")[1])}`}
                  download target="_blank" rel="noreferrer"
                >
                  <FileText className="w-4 h-4 mr-2" /> Genera PDF storico
                </a>
              ) : (
                <span><FileText className="w-4 h-4 mr-2 inline" /> Seleziona un cliente</span>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent data-testid="delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Confermi l'eliminazione?</AlertDialogTitle>
            <AlertDialogDescription>
              Il cliente <b>{deleteTarget?.cognome} {deleteTarget?.nome}</b> verrà rimosso definitivamente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="delete-cancel">Annulla</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} data-testid="delete-confirm" className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Elimina
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
