import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=checking, false=guest, obj=authed
  const [loading, setLoading] = useState(true);

  const check = async () => {
    try {
      const r = await api.get("/auth/me");
      setUser(r.data);
    } catch {
      setUser(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { check(); }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    setUser({ id: r.data.id, email: r.data.email, nome: r.data.nome, role: r.data.role });
    return r.data;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, refresh: check }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
