import { useState } from "react";
import { useYear } from "@/lib/year";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover, PopoverContent, PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Calendar, Plus, Trash2, ChevronDown, Copy, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

export default function YearSelector() {
  const { year, setYear, anni, refresh } = useYear();
  const [openMenu, setOpenMenu] = useState(false);
  const [newYearDialog, setNewYearDialog] = useState(false);
  const [deleteYearDialog, setDeleteYearDialog] = useState(false);
  const [newYear, setNewYear] = useState(() => new Date().getFullYear() + 1);
  const [duplicaDa, setDuplicaDa] = useState("");
  const [processing, setProcessing] = useState(false);

  const openNuovoAnno = () => {
    setOpenMenu(false);
    // Suggerisce l'anno successivo al più recente
    const maxYear = anni.anni.length > 0 ? Math.max(...anni.anni.map((a) => a.anno)) : new Date().getFullYear();
    setNewYear(maxYear + 1);
    setDuplicaDa("");
    setNewYearDialog(true);
  };

  const openEliminaAnno = () => {
    setOpenMenu(false);
    setDeleteYearDialog(true);
  };

  const confermaNuovoAnno = async () => {
    if (!newYear || newYear < 2000 || newYear > 2100) {
      toast.error("Anno non valido");
      return;
    }
    if (anni.anni.some((a) => a.anno === Number(newYear))) {
      toast.error(`L'anno ${newYear} esiste già`);
      return;
    }
    setProcessing(true);
    try {
      const payload = { anno: Number(newYear) };
      if (duplicaDa) payload.duplica_da = Number(duplicaDa);
      const r = await api.post("/anni/apri", payload);
      toast.success(
        r.data.duplicati > 0
          ? `Anno ${newYear} aperto — ${r.data.duplicati} clienti duplicati`
          : `Anno ${newYear} aperto (vuoto)`
      );
      setYear(Number(newYear));
      await refresh();
      setNewYearDialog(false);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore apertura anno");
    } finally {
      setProcessing(false);
    }
  };

  const confermaElimina = async () => {
    setProcessing(true);
    try {
      const r = await api.delete(`/anni/${year}`);
      toast.success(`Anno ${year} eliminato: ${r.data.clienti_eliminati} clienti · ${r.data.lavori_eliminati} lavori`);
      await refresh();
      // Passa a un anno esistente
      const remaining = anni.anni.filter((a) => a.anno !== year);
      if (remaining.length > 0) setYear(remaining[0].anno);
      else setYear(new Date().getFullYear());
      setDeleteYearDialog(false);
    } catch (e) {
      toast.error("Errore eliminazione anno");
    } finally {
      setProcessing(false);
    }
  };

  const currentEntry = anni.anni.find((a) => a.anno === year);

  return (
    <>
      <div className="px-3 py-2 border-b border-border/60 bg-muted/20" data-testid="year-selector">
        <div className="label-mini mb-1.5 flex items-center gap-1.5">
          <Calendar className="w-3 h-3" /> Anno di lavoro
        </div>
        <Popover open={openMenu} onOpenChange={setOpenMenu}>
          <PopoverTrigger asChild>
            <Button variant="outline" className="w-full justify-between h-10 px-3" data-testid="btn-year-menu">
              <div className="text-left">
                <div className="font-mono-num text-lg font-bold leading-none">{year}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  {currentEntry ? `${currentEntry.clienti} clienti` : "nessun dato"}
                </div>
              </div>
              <ChevronDown className="w-4 h-4 opacity-60" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-56 p-1" align="start">
            <div className="max-h-52 overflow-y-auto">
              {anni.anni.map((a) => (
                <button
                  key={a.anno}
                  onClick={() => { setYear(a.anno); setOpenMenu(false); }}
                  className={`w-full flex justify-between items-center px-3 py-2 rounded-md text-sm hover:bg-muted transition-colors ${a.anno === year ? "bg-primary/10 text-primary font-semibold" : ""}`}
                  data-testid={`year-item-${a.anno}`}
                >
                  <span className="font-mono-num">{a.anno}</span>
                  <span className="text-[10px] text-muted-foreground">{a.clienti}</span>
                </button>
              ))}
              {anni.anni.length === 0 && (
                <div className="text-xs text-muted-foreground px-3 py-4 text-center">Nessun anno</div>
              )}
            </div>
            <div className="border-t border-border/60 mt-1 pt-1 space-y-0.5">
              <button
                onClick={openNuovoAnno}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-primary/10 text-primary transition-colors"
                data-testid="btn-apri-anno"
              >
                <Plus className="w-3.5 h-3.5" /> Apri nuovo anno
              </button>
              <button
                onClick={openEliminaAnno}
                disabled={anni.anni.length === 0}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-destructive/10 text-destructive disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                data-testid="btn-elimina-anno"
              >
                <Trash2 className="w-3.5 h-3.5" /> Elimina anno {year}
              </button>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Dialog nuovo anno */}
      <Dialog open={newYearDialog} onOpenChange={setNewYearDialog}>
        <DialogContent data-testid="dialog-nuovo-anno">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-primary" /> Apri nuovo anno
            </DialogTitle>
            <DialogDescription>
              Crea un nuovo anno di lavoro. Puoi partire da zero o duplicare i clienti da un anno esistente.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Anno</Label>
              <Input
                type="number"
                min="2000" max="2100"
                value={newYear}
                onChange={(e) => setNewYear(e.target.value)}
                data-testid="input-nuovo-anno"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Duplica clienti da anno (opzionale)
              </Label>
              <Select value={duplicaDa || "_none"} onValueChange={(v) => setDuplicaDa(v === "_none" ? "" : v)}>
                <SelectTrigger data-testid="select-duplica-da">
                  <SelectValue placeholder="Parti da zero" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">Parti da zero (nessun cliente)</SelectItem>
                  {anni.anni.map((a) => (
                    <SelectItem key={a.anno} value={String(a.anno)}>
                      Duplica da {a.anno} ({a.clienti} clienti)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {duplicaDa && (
                <p className="text-[11px] text-muted-foreground flex items-start gap-1 mt-1">
                  <Copy className="w-3 h-3 mt-0.5 shrink-0" />
                  Copia anagrafica, barca e motore. I costi verranno ricalcolati con le tariffe attuali.
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setNewYearDialog(false)} data-testid="btn-cancel-nuovo-anno">Annulla</Button>
            <Button onClick={confermaNuovoAnno} disabled={processing} className="bg-primary hover:bg-primary/90" data-testid="btn-conferma-nuovo-anno">
              {processing ? "Creazione…" : "Apri anno"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AlertDialog elimina anno */}
      <AlertDialog open={deleteYearDialog} onOpenChange={setDeleteYearDialog}>
        <AlertDialogContent data-testid="dialog-elimina-anno">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-destructive" />
              Eliminare l'anno {year}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Verranno eliminati definitivamente <b>{currentEntry?.clienti || 0} clienti</b> e tutti i lavori dell'anno {year}.
              I dati di altri anni non saranno toccati. L'operazione non è reversibile.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="btn-cancel-elimina">Annulla</AlertDialogCancel>
            <AlertDialogAction onClick={confermaElimina} disabled={processing} className="bg-destructive text-destructive-foreground hover:bg-destructive/90" data-testid="btn-conferma-elimina-anno">
              {processing ? "Eliminazione…" : "Sì, elimina anno"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
