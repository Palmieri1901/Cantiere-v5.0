import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/lib/auth";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Clienti from "@/pages/Clienti";
import Tariffe from "@/pages/Tariffe";
import PostiBarca from "@/pages/PostiBarca";
import Impostazioni from "@/pages/Impostazioni";
import Login from "@/pages/Login";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <ProtectedRoute><Home /></ProtectedRoute>
            } />
            <Route element={
              <ProtectedRoute><Layout /></ProtectedRoute>
            }>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clienti" element={<Clienti />} />
              <Route path="/posti-barca" element={<PostiBarca />} />
              <Route path="/tariffe" element={<Tariffe />} />
              <Route path="/impostazioni" element={<Impostazioni />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
