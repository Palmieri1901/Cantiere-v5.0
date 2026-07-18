import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Building2, Upload, Save, RefreshCw, Trash2, ImageIcon } from "lucide-react";

const FIELDS = [
  { key: "nome", label: "Nome cantiere *", placeholder: "Es. Cantiere Portomare" },
  { key: "slogan", label: "Slogan", placeholder: "Es. Cantiere nautico dal 1985" },
  { key: "indirizzo", label: "Indirizzo", placeholder: "Via Marina, 42" },
  { key: "citta", label: "Città", placeholder: "Genova" },
  { key: "cap", label: "CAP", placeholder: "16128" },
  { key: "provincia", label: "Provincia", placeholder: "GE" },
  { key: "telefono", label: "Telefono", placeholder: "+39 010 123 4567" },
  { key: "email", label: "Email", placeholder: "info@cantiere.it" },
  { key: "sito_web", label: "Sito web", placeholder: "www.cantiere.it" },
  { key: "piva", label: "Partita IVA", placeholder: "01234567890" },
];

export default function Impostazioni() {
  const [c, setC] = useState(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const load = () => api.get("/cantiere").then((r) => setC(r.data));
  useEffect(() => { load(); }, []);

  const update = (k, v) => setC((prev) => ({ ...prev, [k]: v }));

  const save = async () => {
    if (!c.nome) {
      toast.error("Il nome del cantiere è obbligatorio");
      return;
    }
    setSaving(true);
    try {
      const payload = Object.fromEntries(FIELDS.map(f => [f.key, c[f.key] ?? ""]));
      payload.orari = c.orari ?? "";
      payload.logo_base64 = c.logo_base64 ?? "";
      await api.put("/cantiere", payload);
      toast.success("Informazioni salvate");
      load();
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const onLogoSelected = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Seleziona un file immagine");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Immagine troppo grande (max 2MB)");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => update("logo_base64", reader.result);
    reader.readAsDataURL(file);
  };

  if (!c) return <div className="p-8 text-muted-foreground">Caricamento…</div>;

  return (
    <div className="p-6 md:p-10 max-w-5xl" data-testid="impostazioni-page">
      <div className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 label-mini mb-2">
            <Building2 className="w-3.5 h-3.5" /> Impostazioni cantiere
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Informazioni & Logo</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl">
            Configura nome, indirizzo, contatti e logo del cantiere. Queste informazioni compaiono nella pagina iniziale e nei preventivi PDF.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} data-testid="btn-reload">
            <RefreshCw className="w-4 h-4 mr-2" /> Ricarica
          </Button>
          <Button onClick={save} disabled={saving} className="bg-primary hover:bg-primary/90" data-testid="btn-save-cantiere">
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Salvataggio…" : "Salva"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Logo */}
        <Card className="p-6 h-fit" data-testid="logo-card">
          <div className="label-mini mb-3">Logo</div>
          <div className="aspect-square bg-muted/40 border border-dashed border-border rounded-md grid place-items-center overflow-hidden mb-3">
            {c.logo_base64 ? (
              <img src={c.logo_base64} alt="Logo" className="max-w-full max-h-full object-contain p-4" data-testid="logo-preview" />
            ) : (
              <div className="text-center text-muted-foreground p-6">
                <ImageIcon className="w-10 h-10 mx-auto mb-2 opacity-40" />
                <div className="text-xs">Nessun logo caricato</div>
              </div>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onLogoSelected} data-testid="input-logo-file" />
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => fileRef.current?.click()} className="flex-1" data-testid="btn-upload-logo">
              <Upload className="w-4 h-4 mr-2" />
              Carica
            </Button>
            {c.logo_base64 && (
              <Button variant="outline" onClick={() => update("logo_base64", "")} data-testid="btn-remove-logo">
                <Trash2 className="w-4 h-4 text-destructive" />
              </Button>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            Formati: PNG, JPG, SVG. Max 2MB. Sfondo trasparente consigliato.
          </p>
        </Card>

        {/* Info */}
        <Card className="p-6 lg:col-span-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {FIELDS.map((f) => (
              <div key={f.key} className={f.key === "nome" || f.key === "slogan" || f.key === "indirizzo" ? "md:col-span-2" : ""}>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{f.label}</Label>
                <Input
                  value={c[f.key] ?? ""}
                  onChange={(e) => update(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="mt-1.5"
                  data-testid={`input-${f.key}`}
                />
              </div>
            ))}
          </div>
          <Separator />
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Orari di apertura</Label>
            <Textarea
              value={c.orari ?? ""}
              onChange={(e) => update("orari", e.target.value)}
              placeholder="Lun-Ven 8:30-12:30 · 14:30-18:30&#10;Sabato 8:30-12:30&#10;Domenica chiuso"
              rows={3}
              className="mt-1.5"
              data-testid="input-orari"
            />
          </div>
        </Card>
      </div>
    </div>
  );
}
