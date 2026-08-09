import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useYear } from "@/lib/year";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Popover, PopoverContent, PopoverTrigger
} from "@/components/ui/popover";
import { Anchor, Waves } from "lucide-react";

export default function PostiBarca() {
  const [posti, setPosti] = useState([]);
  const [loading, setLoading] = useState(true);
  const { year } = useYear();

  useEffect(() => {
    setLoading(true);
    api.get(`/posti-barca?anno=${year}`).then((r) => {
      setPosti(r.data);
      setLoading(false);
    });
  }, [year]);

  const occupati = posti.filter((p) => p.occupato).length;
  const dentro = posti.filter((p) => p.tipo_sosta === "dentro").length;
  const fuori = posti.filter((p) => p.tipo_sosta === "fuori").length;

  return (
    <div className="p-6 md:p-10 max-w-[1400px]" data-testid="posti-barca-page">
      <div className="mb-8">
        <div className="label-mini mb-2">Vista cantiere</div>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Posti barca</h1>
        <p className="text-muted-foreground mt-1">
          Griglia dei 200 posti barca. Clicca su un posto per vedere i dettagli.
        </p>
      </div>

      {/* Legenda */}
      <Card className="p-4 mb-6 flex flex-wrap gap-6">
        <Stat label="Totali" value={200} />
        <Stat label="Occupati" value={occupati} className="text-primary" />
        <Stat label="Liberi" value={200 - occupati} />
        <Stat label="Al coperto" value={dentro} />
        <Stat label="Su piazzale" value={fuori} />
        <div className="flex items-center gap-4 ml-auto text-xs">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-primary" />Coperto</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-chart-2" />Fuori</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-border bg-background" />Libero</span>
        </div>
      </Card>

      {loading ? (
        <div className="text-muted-foreground py-16 text-center">Caricamento posti…</div>
      ) : (
        <Card className="p-6">
          <div className="grid grid-cols-10 sm:grid-cols-15 md:grid-cols-20 gap-1.5" data-testid="posti-grid">
            {posti.map((p) => {
              const bg = !p.occupato
                ? "bg-background border border-border hover:border-primary/40"
                : p.tipo_sosta === "dentro"
                ? "bg-primary text-primary-foreground border border-primary"
                : "bg-chart-2 text-white border border-chart-2";
              return (
                <Popover key={p.numero}>
                  <PopoverTrigger asChild>
                    <button
                      className={`aspect-square rounded-sm text-[10px] font-mono-num font-semibold transition-transform hover:scale-110 ${bg}`}
                      data-testid={`posto-${p.numero}`}
                      title={p.occupato ? p.cliente_nome : `Posto ${p.numero} libero`}
                    >
                      {p.numero}
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 bg-popover">
                    <div className="label-mini mb-1">Posto #{String(p.numero).padStart(3, "0")}</div>
                    {p.occupato ? (
                      <>
                        <div className="font-display text-lg font-semibold">{p.cliente_nome}</div>
                        <div className="text-sm text-muted-foreground mt-1">{p.tipo_barca}</div>
                        <Badge
                          className="mt-3"
                          variant="outline"
                        >
                          {p.tipo_sosta === "dentro" ? (
                            <><Waves className="w-3 h-3 mr-1" /> Sosta al coperto</>
                          ) : (
                            <><Anchor className="w-3 h-3 mr-1" /> Sosta a terra</>
                          )}
                        </Badge>
                      </>
                    ) : (
                      <>
                        <div className="font-display text-lg font-semibold">Libero</div>
                        <div className="text-sm text-muted-foreground mt-1">
                          Assegna un cliente dalla pagina Clienti.
                        </div>
                      </>
                    )}
                  </PopoverContent>
                </Popover>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, className = "" }) {
  return (
    <div>
      <div className="label-mini">{label}</div>
      <div className={`font-mono-num text-2xl font-semibold ${className}`}>{value}</div>
    </div>
  );
}
