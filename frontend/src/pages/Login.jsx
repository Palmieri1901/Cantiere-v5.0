import { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sailboat, LogIn, AlertCircle } from "lucide-react";

function formatError(detail) {
  if (!detail) return "Errore imprevisto";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || JSON.stringify(e)).join(" · ");
  return String(detail);
}

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  if (user && user !== false) return <Navigate to={loc.state?.from || "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      nav(loc.state?.from || "/", { replace: true });
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || "Impossibile accedere");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-secondary/40 to-background grid place-items-center px-4" data-testid="login-page">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-lg bg-primary text-primary-foreground grid place-items-center mb-4">
            <Sailboat className="w-8 h-8" strokeWidth={1.8} />
          </div>
          <div className="label-mini mb-1">Gestione Cantiere</div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Portomare</h1>
        </div>

        <Card className="p-8">
          <h2 className="font-display text-2xl font-semibold mb-1">Accedi</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Inserisci le tue credenziali per accedere al gestionale.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@portomare.it"
                required
                autoFocus
                data-testid="input-login-email"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="input-login-password"
              />
            </div>

            {err && (
              <div className="flex items-start gap-2 p-3 rounded-md bg-destructive/10 border border-destructive/30 text-destructive text-sm" data-testid="login-error">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{err}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-primary/90"
              data-testid="btn-login"
            >
              <LogIn className="w-4 h-4 mr-2" />
              {loading ? "Accesso…" : "Accedi"}
            </Button>
          </form>
        </Card>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Portomare · Gestionale Cantiere Nautico
        </p>
      </div>
    </div>
  );
}
