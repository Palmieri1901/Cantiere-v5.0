import { useEffect, useMemo, useState } from "react";
import { api, API } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { FileSignature, Download, User, RefreshCw } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useYear } from "@/lib/year";

export default function Contratti() {
  const { year } = useYear();
  const [clienti, setClienti] = useState([]);
  const [cantiere, setCantiere] = useState(null);
  const [clienteId, setClienteId] = useState("");
  const [titolo, setTitolo] = useState("CONTRATTO DI RIMESSAGGIO INVERNALE E MANUTENZIONE");
  const [testo, setTesto] = useState("");
  const [generating, setGenerating] = useState(false);

  const load = () => {
    api.get(`/clienti?anno=${year}`).then((r) => setClienti(r.data || []));
    api.get("/cantiere").then((r) => {
      setCantiere(r.data);
      setTesto((prev) => prev || r.data.contratto_template || "");
    });
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [year]);

  const resetTemplate = () => {
    setTesto(cantiere?.contratto_template || "");
    toast.success("Testo ripristinato dal template");
  };

  const clienteScelto = useMemo(
    () => clienti.find((c) => c.id === clienteId) || null,
    [clienti, clienteId]
  );

  const generatePdf = async () => {
    if (!clienteId) { toast.error("Seleziona un cliente"); return; }
    if (!testo.trim()) { toast.error("Il testo del contratto non può essere vuoto"); return; }
    setGenerating(true);
    try {
      const res = await api.post("/contratti/pdf", { cliente_id: clienteId, testo, titolo }, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contratto_${clienteScelto?.cognome || "cliente"}_${clienteScelto?.nome || ""}.pdf`.toLowerCase().replace(/\s+/g, "_");
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Contratto PDF generato");
    } catch (e) {
      toast.error("Errore nella generazione del contratto");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-6 md:p-10 max-w-5xl" data-testid="contratti-page">
      <div className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 label-mini mb-2">
            <FileSignature className="w-3.5 h-3.5" /> Contratti
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Genera contratto firma-cliente</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl">
            Scegli un cliente, personalizza titolo e clausole, poi scarica un PDF pronto per la firma.
            Il testo di partenza viene dal template modificabile in Impostazioni.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" onClick={resetTemplate} data-testid="btn-reset-template">
            <RefreshCw className="w-4 h-4 mr-2" /> Ripristina template
          </Button>
          <Button onClick={generatePdf} disabled={generating || !clienteId} className="bg-primary hover:bg-primary/90" data-testid="btn-generate-contratto">
            <Download className="w-4 h-4 mr-2" />
            {generating ? "Generazione…" : "Scarica PDF"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 h-fit lg:col-span-1 space-y-4">
          <div>
            <div className="label-mini mb-2 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" /> Cliente
            </div>
            <Select value={clienteId} onValueChange={setClienteId}>
              <SelectTrigger data-testid="select-cliente"><SelectValue placeholder="Seleziona un cliente" /></SelectTrigger>
              <SelectContent>
                {clienti.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.cognome} {c.nome} · {c.tipo_barca}{c.posto_barca ? ` · #${String(c.posto_barca).padStart(3, "0")}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {clienteScelto && (
            <div className="pt-3 border-t border-border/60 text-sm space-y-1.5" data-testid="cliente-anagrafica">
              <div className="font-semibold">{clienteScelto.cognome} {clienteScelto.nome}</div>
              <div className="text-muted-foreground">{clienteScelto.tipo_barca} · L. {clienteScelto.lunghezza} m</div>
              {clienteScelto.codice_fiscale && <div className="text-muted-foreground">CF: {clienteScelto.codice_fiscale}</div>}
              {clienteScelto.indirizzo && <div className="text-muted-foreground">{clienteScelto.indirizzo}</div>}
              {(clienteScelto.telefono || clienteScelto.cellulare) && (
                <div className="text-muted-foreground">
                  {[clienteScelto.telefono, clienteScelto.cellulare].filter(Boolean).join(" · ")}
                </div>
              )}
              {clienteScelto.email && <div className="text-muted-foreground">{clienteScelto.email}</div>}
              {clienteScelto.posto_barca && (
                <div className="text-muted-foreground">Posto barca: #{String(clienteScelto.posto_barca).padStart(3, "0")}</div>
              )}
            </div>
          )}
        </Card>

        <Card className="p-6 lg:col-span-2 space-y-4">
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Titolo contratto</Label>
            <Input
              value={titolo}
              onChange={(e) => setTitolo(e.target.value)}
              className="mt-1.5"
              data-testid="input-titolo-contratto"
            />
          </div>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Testo contratto e clausole</Label>
            <Textarea
              value={testo}
              onChange={(e) => setTesto(e.target.value)}
              rows={22}
              className="mt-1.5 font-mono text-xs leading-relaxed"
              data-testid="input-testo-contratto"
            />
            <p className="text-[11px] text-muted-foreground mt-1.5">
              Ogni riga vuota diventa una spaziatura nel PDF. Usa <code className="font-mono">**parola**</code> per il grassetto. In fondo viene aggiunto automaticamente lo spazio per luogo, data e firma. Segnaposto disponibili: <code className="font-mono">{"{{cognome}}"}</code>, <code className="font-mono">{"{{nome}}"}</code>, <code className="font-mono">{"{{codice_fiscale}}"}</code>, <code className="font-mono">{"{{indirizzo}}"}</code>, <code className="font-mono">{"{{telefono}}"}</code>, <code className="font-mono">{"{{email}}"}</code>, <code className="font-mono">{"{{tipo_barca}}"}</code>, <code className="font-mono">{"{{lunghezza}}"}</code>, <code className="font-mono">{"{{potenza_motore}}"}</code>, <code className="font-mono">{"{{posto_barca}}"}</code>, <code className="font-mono">{"{{data_oggi}}"}</code>.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
