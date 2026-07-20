import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { YearProvider } from "@/lib/year";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Clienti from "@/pages/Clienti";
import Tariffe from "@/pages/Tariffe";
import PostiBarca from "@/pages/PostiBarca";
import Impostazioni from "@/pages/Impostazioni";
import Report from "@/pages/Report";

function App() {
  return (
    <div className="App">
      <YearProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clienti" element={<Clienti />} />
              <Route path="/posti-barca" element={<PostiBarca />} />
              <Route path="/tariffe" element={<Tariffe />} />
              <Route path="/impostazioni" element={<Impostazioni />} />
              <Route path="/report" element={<Report />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </YearProvider>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
