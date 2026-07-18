import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Clienti from "@/pages/Clienti";
import Tariffe from "@/pages/Tariffe";
import PostiBarca from "@/pages/PostiBarca";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/clienti" element={<Clienti />} />
            <Route path="/posti-barca" element={<PostiBarca />} />
            <Route path="/tariffe" element={<Tariffe />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
