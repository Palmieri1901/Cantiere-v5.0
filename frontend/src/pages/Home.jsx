import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, API } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sailboat, MapPin, Phone, Mail, Clock, ArrowRight, Anchor, Building2, Globe, Database, Download, Upload, AlertTriangle, FileText, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";
import ClienteForm from "@/pages/ClienteForm";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";

export default function Home() {
  const [c, setC] = useState(null);
  const [stats, setStats] = useState(null);
  const restoreRef = useRef(null);
  const [restoreData, setRestoreData] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [openPreventivo, setOpenPreventivo] = useState(false);

  const load = () => {
    api.get("/cantiere").then((r) => setC(r.data));
    api.get("/stats").then((r) => setStats(r.data));
  };

  useEffect(() => { load(); }, []);

  const onRestoreSelected = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        if (!data.clienti && !data.tariffe && !data.cantiere) {
          toast.error("File di backup non valido");
          return;
        }
        setRestoreData(data);
      } catch {
        toast.error("File JSON non valido");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const doRestore = async () => {
    if (!restoreData) return;
    setRestoring(true);
    try {
      const r = await api.post("/restore", restoreData);
      const rst = r.data.restored;
      toast.success(`Ripristinati: ${rst.clienti} clienti, ${rst.lavori} lavori`);
      setRestoreData(null);
      load();
    } catch {
      toast.error("Errore durante il ripristino");
    } finally {
      setRestoring(false);
    }
  };

  if (!c) return <div className="p-8 text-muted-foreground">Caricamento…</div>;

  const address = [c.indirizzo, [c.cap, c.citta, c.provincia && `(${c.provincia})`].filter(Boolean).join(" ")].filter(Boolean).join(", ");

  return (
    <div className="min-h-screen bg-background" data-testid="home-page">
      {/* Hero */}
      <div className="relative overflow-hidden bg-gradient-to-b from-secondary/40 to-background border-b border-border">
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{
          backgroundImage: "radial-gradient(circle at 20% 30%, hsl(var(--primary)) 1px, transparent 1px), radial-gradient(circle at 80% 70%, hsl(var(--chart-2)) 1px, transparent 1px)",
          backgroundSize: "60px 60px, 80px 80px",
        }} />
        <div className="relative max-w-6xl mx-auto px-6 md:px-10 py-16 md:py-24">
          {c.logo_base64 ? (
            <img src={c.logo_base64} alt="Logo" className="h-20 md:h-24 mb-6 object-contain" data-testid="home-logo" />
          ) : (
            <div className="w-16 h-16 rounded-lg bg-primary text-primary-foreground grid place-items-center mb-6">
              <Sailboat className="w-9 h-9" strokeWidth={1.8} />
            </div>
          )}

          <div className="label-mini mb-3">Cantiere Nautico</div>
          <h1 className="font-display text-5xl md:text-7xl font-semibold tracking-tight text-foreground leading-[1.02]">
            {c.nome}
          </h1>
          {c.slogan && (
            <p className="mt-4 text-lg md:text-xl text-muted-foreground max-w-2xl font-display italic">
              {c.slogan}
            </p>
          )}

          <div className="mt-10 flex flex-wrap gap-3">
            <Button asChild size="lg" className="bg-primary hover:bg-primary/90" data-testid="cta-dashboard">
              <Link to="/dashboard">
                Vai al gestionale
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" data-testid="cta-clienti">
              <Link to="/clienti">Gestione clienti</Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => setOpenPreventivo(true)}
              data-testid="cta-preventivo-veloce"
              className="border-primary/40 text-primary hover:bg-primary/10"
            >
              <FileText className="w-4 h-4 mr-2" />
              Preventivo veloce (PDF)
            </Button>
            <Button asChild variant="outline" size="lg" data-testid="cta-listino-pdf" className="border-primary/40 text-primary hover:bg-primary/10">
              <a href={`${API}/tariffe/listino.pdf`} target="_blank" rel="noreferrer">
                <FileText className="w-4 h-4 mr-2" />
                Listino prezzi (PDF)
              </a>
            </Button>
            <Button asChild variant="outline" size="lg" data-testid="cta-export-excel" className="border-primary/40 text-primary hover:bg-primary/10">
              <a href={`${API}/export/clienti.xlsx?anno=${new Date().getFullYear()}`} download>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Excel clienti (commercialista)
              </a>
            </Button>
            <Button asChild variant="ghost" size="lg" data-testid="cta-impostazioni">
              <Link to="/impostazioni">Modifica info cantiere</Link>
            </Button>
          </div>
        </div>
      </div>

      <ClienteForm open={openPreventivo} onOpenChange={setOpenPreventivo} mode="preventivo" />

      {/* Info + stats */}
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-14 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contatti */}
        <Card className="p-6 lg:col-span-2" data-testid="home-contatti">
          <div className="label-mini mb-4 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5" /> Sede & contatti
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {address && (
              <InfoBlock icon={MapPin} label="Indirizzo" testId="info-indirizzo">
                {address}
              </InfoBlock>
            )}
            {c.telefono && (
              <InfoBlock icon={Phone} label="Telefono" testId="info-telefono">
                <a href={`tel:${c.telefono}`} className="hover:text-primary">{c.telefono}</a>
              </InfoBlock>
            )}
            {c.email && (
              <InfoBlock icon={Mail} label="Email" testId="info-email">
                <a href={`mailto:${c.email}`} className="hover:text-primary">{c.email}</a>
              </InfoBlock>
            )}
            {c.orari && (
              <InfoBlock icon={Clock} label="Orari" testId="info-orari">
                {c.orari}
              </InfoBlock>
            )}
            {c.sito_web && (
              <InfoBlock icon={Globe} label="Sito web" testId="info-sito">
                <a href={c.sito_web.startsWith("http") ? c.sito_web : `https://${c.sito_web}`} target="_blank" rel="noreferrer" className="hover:text-primary">
                  {c.sito_web}
                </a>
              </InfoBlock>
            )}
            {c.piva && (
              <InfoBlock icon={Building2} label="P.IVA" testId="info-piva">
                {c.piva}
              </InfoBlock>
            )}
          </div>

          {!address && !c.telefono && !c.email && !c.orari && (
            <div className="text-sm text-muted-foreground bg-muted/40 rounded-md p-4 border border-dashed border-border">
              Nessuna informazione impostata. <Link to="/impostazioni" className="text-primary underline">Aggiungi ora →</Link>
            </div>
          )}
        </Card>

        {/* Stats */}
        <Card className="p-6 bg-primary/5 border-primary/30" data-testid="home-stats">
          <div className="label-mini mb-4 flex items-center gap-1.5">
            <Anchor className="w-3.5 h-3.5 text-primary" /> Attività in corso
          </div>
          {stats ? (
            <div className="space-y-4">
              <StatBlock label="Clienti gestiti" value={stats.totale_clienti} />
              <StatBlock label="Posti barca occupati" value={`${stats.posti_occupati} / ${stats.posti_totali}`} />
              <StatBlock label="Entrate stimate" value={new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(stats.entrate_totali)} highlight />
            </div>
          ) : (
            <div className="text-muted-foreground text-sm">Caricamento…</div>
          )}
        </Card>
      </div>

      {/* Backup & Ripristino */}
      <div className="max-w-6xl mx-auto px-6 md:px-10 pb-14">
        <Card className="p-6" data-testid="home-backup">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 label-mini mb-2">
                <Database className="w-3.5 h-3.5" /> Backup dati
              </div>
              <h3 className="font-display text-xl font-semibold">Salva & Recupera tutti i dati</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
                Scarica un file di backup con clienti, lavori, tariffe e informazioni del cantiere.
                Puoi conservarlo come archivio o ripristinarlo in caso di problemi.
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button asChild variant="outline" size="lg" data-testid="btn-home-backup-download">
                <a href={`${API}/backup`} download>
                  <Download className="w-4 h-4 mr-2" />
                  Salva backup
                </a>
              </Button>
              <input ref={restoreRef} type="file" accept="application/json,.json" hidden onChange={onRestoreSelected} data-testid="input-home-restore-file" />
              <Button variant="outline" size="lg" onClick={() => restoreRef.current?.click()} data-testid="btn-home-restore-open">
                <Upload className="w-4 h-4 mr-2" />
                Recupera backup
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <AlertDialog open={!!restoreData} onOpenChange={(o) => !o && setRestoreData(null)}>
        <AlertDialogContent data-testid="home-restore-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-destructive" />
              Confermi il ripristino?
            </AlertDialogTitle>
            <AlertDialogDescription>
              <div className="space-y-2 mt-2">
                <div>Il backup contiene:</div>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  <li><b>{restoreData?.clienti?.length || 0}</b> clienti</li>
                  <li><b>{restoreData?.lavori?.length || 0}</b> lavori</li>
                  <li>Tariffe: <b>{restoreData?.tariffe ? "sì" : "no"}</b></li>
                  <li>Cantiere: <b>{restoreData?.cantiere ? "sì" : "no"}</b></li>
                </ul>
                <div className="text-destructive mt-3 text-sm font-medium">
                  ⚠️ Tutti i dati attuali verranno sovrascritti. L'operazione non è reversibile.
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="home-restore-cancel">Annulla</AlertDialogCancel>
            <AlertDialogAction onClick={doRestore} disabled={restoring} className="bg-destructive text-destructive-foreground hover:bg-destructive/90" data-testid="home-restore-confirm">
              {restoring ? "Ripristino…" : "Sì, ripristina"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function InfoBlock({ icon: Icon, label, children, testId }) {
  return (
    <div data-testid={testId}>
      <div className="flex items-center gap-1.5 label-mini mb-1.5">
        <Icon className="w-3 h-3" /> {label}
      </div>
      <div className="text-sm text-foreground leading-relaxed">{children}</div>
    </div>
  );
}

function StatBlock({ label, value, highlight }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`font-display font-mono-num text-2xl mt-0.5 ${highlight ? "text-primary font-bold" : "font-semibold"}`}>
        {value}
      </div>
    </div>
  );
}
