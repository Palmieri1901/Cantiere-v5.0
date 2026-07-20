import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const YearCtx = createContext(null);

const STORAGE_KEY = "portomare_selected_year";

export function YearProvider({ children }) {
  const [year, setYearState] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? parseInt(stored, 10) : new Date().getFullYear();
  });
  const [anni, setAnni] = useState({ anno_corrente: new Date().getFullYear(), anni: [] });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await api.get("/anni");
      setAnni(r.data);
      // Se l'anno selezionato non esiste nei dati e non è quello corrente, torna al corrente
      if (r.data.anni.length > 0 && !r.data.anni.some((a) => a.anno === year)) {
        const fallback = r.data.anni[0].anno;
        setYearState(fallback);
        localStorage.setItem(STORAGE_KEY, String(fallback));
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => { refresh(); }, []); // eslint-disable-line

  const setYear = (y) => {
    setYearState(y);
    localStorage.setItem(STORAGE_KEY, String(y));
  };

  return (
    <YearCtx.Provider value={{ year, setYear, anni, refresh, loading }}>
      {children}
    </YearCtx.Provider>
  );
}

export function useYear() {
  return useContext(YearCtx);
}
