import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Index from "./pages/Index";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import ErrorBoundary from "./components/ErrorBoundary";
import { useState, useEffect } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Protected Route Component
const AuthGuard = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem("vidhi_auth");
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

// Redirect logged-in users away from login page
const LoginGuard = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem("vidhi_auth");
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
};

const App = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Toaster />
          <Sonner />

          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginGuard><Login /></LoginGuard>} />
              <Route path="/" element={<AuthGuard><ErrorBoundary><Index /></ErrorBoundary></AuthGuard>} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
