import { useEffect, useState } from "react";
import { api, fmtEuro } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Wrench } from "lucide-react";

const TIPI_LAVORO = ["Antivegetativa", "Manutenzione motore", "Riparazione", "Pulizia", "Elettrico", "Altro"];
const STATI = [
  { value: "pianificato", label: "Pianificato" },
  { value: "in_corso", label: "In corso" },
  { value: "completato", label: "Completato" },
];

const emptyLavoro = (cliente_id) => ({
  cliente_id,
  data: new Date().toISOString().slice(0, 10),
  tipo: "Manutenzione motore",
  descrizione: "",
  costo: 0,
  materiali: "",
  stato: "completato",
});

export default function LavoriSection({ clienteId }) {
  const [lavori, setLavori] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(null);

  const load = () => {
    if (!clienteId) return;
    setLoading(true);
    api.get(`/clienti/${clienteId}/lavori`).then((r) => {
      setLavori(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [clienteId]);

  const openNew = () => {
    setEditing(null);
    setForm(emptyLavoro(clienteId));
    setDialogOpen(true);
  };

  const openEdit = (l) => {
    setEditing(l);
    setForm({ ...l });
    setDialogOpen(true);
  };

  const save = async () => {
    if (!form.tipo || !form.data) {
      toast.error("Data e tipo sono obbligatori");
      return;
    }
    const payload = { ...form, costo: Number(form.costo) || 0 };
    try {
      if (editing) {
        await api.put(`/lavori/${editing.id}`, payload);
        toast.success("Lavoro aggiornato");
      } else {
        await api.post("/lavori", payload);
        toast.success("Lavoro aggiunto");
      }
      setDialogOpen(false);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore salvataggio");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Eliminare questo lavoro?")) return;
    await api.delete(`/lavori/${id}`);
    toast.success("Lavoro eliminato");
    load();
  };

  const totale = lavori.reduce((s, l) => s + (l.costo || 0), 0);

  if (!clienteId) {
    return (
      <div className="text-sm text-muted-foreground p-4 bg-muted/40 rounded-md">
        Salva il cliente per poter aggiungere lo storico lavori.
      </div>
    );
  }

  return (
    <div data-testid="lavori-section">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="label-mini flex items-center gap-1.5"><Wrench className="w-3 h-3" /> Storico lavori</div>
          <div className="text-xs text-muted-foreground mt-1">
            {lavori.length} interventi · totale {fmtEuro(totale)}
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={openNew} data-testid="btn-nuovo-lavoro">
          <Plus className="w-3.5 h-3.5 mr-1.5" /> Aggiungi lavoro
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-muted-foreground py-4">Caricamento…</div>
      ) : lavori.length === 0 ? (
        <div className="text-sm text-muted-foreground py-6 text-center bg-muted/30 rounded-md border border-dashed border-border">
          Nessun lavoro registrato. Aggiungi il primo intervento.
        </div>
      ) : (
        <div className="border border-border rounded-md divide-y divide-border">
          {lavori.map((l) => (
            <div key={l.id} className="p-3 flex items-center gap-3 hover:bg-muted/40" data-testid={`lavoro-row-${l.id}`}>
              <div className="w-20 shrink-0">
                <div className="font-mono-num text-xs text-muted-foreground">{l.data}</div>
                <StatusBadge stato={l.stato} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{l.tipo}</div>
                {l.descrizione && <div className="text-xs text-muted-foreground truncate">{l.descrizione}</div>}
                {l.materiali && <div className="text-[11px] text-muted-foreground/80 italic mt-0.5">Mat.: {l.materiali}</div>}
              </div>
              <div className="font-mono-num text-sm font-semibold shrink-0">{fmtEuro(l.costo)}</div>
              <div className="flex gap-0.5 shrink-0">
                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(l)} data-testid={`btn-edit-lavoro-${l.id}`}>
                  <Pencil className="w-3.5 h-3.5" />
                </Button>
                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => remove(l.id)} data-testid={`btn-delete-lavoro-${l.id}`}>
                  <Trash2 className="w-3.5 h-3.5 text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="lavoro-dialog">
          <DialogHeader>
            <DialogTitle>{editing ? "Modifica lavoro" : "Nuovo lavoro"}</DialogTitle>
            <DialogDescription>Registra un intervento eseguito o pianificato.</DialogDescription>
          </DialogHeader>
          {form && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Data</Label>
                  <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} data-testid="input-lavoro-data" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tipo</Label>
                  <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                    <SelectTrigger data-testid="select-lavoro-tipo"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIPI_LAVORO.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Descrizione</Label>
                <Input value={form.descrizione} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} placeholder="Es. Cambio olio motore, revisione elica…" data-testid="input-lavoro-descrizione" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Costo</Label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">€</span>
                    <Input type="number" step="0.01" min="0" className="pl-10 font-mono-num" value={form.costo} onChange={(e) => setForm({ ...form, costo: e.target.value })} data-testid="input-lavoro-costo" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Stato</Label>
                  <Select value={form.stato} onValueChange={(v) => setForm({ ...form, stato: v })}>
                    <SelectTrigger data-testid="select-lavoro-stato"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {STATI.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Materiali</Label>
                <Textarea rows={2} value={form.materiali} onChange={(e) => setForm({ ...form, materiali: e.target.value })} placeholder="Es. 3L vernice antivegetativa, filtro olio…" data-testid="input-lavoro-materiali" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} data-testid="btn-lavoro-annulla">Annulla</Button>
            <Button onClick={save} className="bg-primary hover:bg-primary/90" data-testid="btn-lavoro-salva">Salva</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatusBadge({ stato }) {
  const map = {
    pianificato: { label: "Pianificato", cls: "bg-muted text-muted-foreground border-border" },
    in_corso: { label: "In corso", cls: "bg-chart-3/20 text-chart-3 border-chart-3/40" },
    completato: { label: "Completato", cls: "bg-primary/10 text-primary border-primary/30" },
  };
  const s = map[stato] || map.completato;
  return (
    <Badge variant="outline" className={`text-[9px] mt-1 ${s.cls}`}>{s.label}</Badge>
  );
}
