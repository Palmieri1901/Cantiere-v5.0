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
import { Plus, Search, Pencil, Trash2, FileSpreadsheet, FileDown, FileText } from "lucide-react";
import { toast } from "sonner";
import ClienteForm from "@/pages/ClienteForm";
import { API } from "@/lib/api";

export default function Clienti() {
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [tipoSostaFilter, setTipoSostaFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = () => {
    setLoading(true);
    api.get("/clienti").then((r) => {
      setClienti(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    return clienti.filter((c) => {
      if (tipoSostaFilter !== "all" && c.tipo_sosta !== tipoSostaFilter) return false;
      if (!q) return true;
      const s = q.toLowerCase();
      return (
        c.nome?.toLowerCase().includes(s) ||
        c.cognome?.toLowerCase().includes(s) ||
        c.tipo_barca?.toLowerCase().includes(s) ||
        String(c.posto_barca || "").includes(s)
      );
    });
  }, [clienti, q, tipoSostaFilter]);

  const totale = (c) =>
    (c.costo_sosta || 0) + (c.costo_copertura || 0) + (c.costo_alaggio || 0) +
    (c.costo_varo || 0) + (c.costo_antivegetativa || 0) + (c.costo_manutenzione_motore || 0);

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

  return (
    <div className="p-6 md:p-10 max-w-[1400px]" data-testid="clienti-page">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <div className="label-mini mb-2">Anagrafica</div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Clienti</h1>
          <p className="text-muted-foreground mt-1">{clienti.length} clienti registrati</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild data-testid="btn-export-csv">
            <a href={`${API}/export/clienti.csv`} download>
              <FileDown className="w-4 h-4 mr-2" /> CSV
            </a>
          </Button>
          <Button variant="outline" asChild data-testid="btn-export-xlsx">
            <a href={`${API}/export/clienti.xlsx`} download>
              <FileSpreadsheet className="w-4 h-4 mr-2" /> Excel
            </a>
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
              <SelectItem value="fuori">Sosta fuori</SelectItem>
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
              <TableHead className="text-right">Totale</TableHead>
              <TableHead className="w-32 text-right">Azioni</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7} className="py-8 text-center text-muted-foreground">Caricamento…</TableCell></TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-16 text-center">
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
                        : "border-chart-2/50"}
                    >
                      {c.tipo_sosta === "dentro" ? "Coperto" : "Fuori"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono-num font-semibold">{fmtEuro(totale(c))}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
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
