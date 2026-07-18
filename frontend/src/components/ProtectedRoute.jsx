import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const loc = useLocation();

  if (loading || user === null) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground" data-testid="auth-loading">
        Caricamento…
      </div>
    );
  }
  if (user === false) {
    return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  }
  return children;
}
