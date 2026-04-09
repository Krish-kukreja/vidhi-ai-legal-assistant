import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Index from "./pages/Index";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import { useState, useEffect } from "react";

const queryClient = new QueryClient();

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
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />

        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginGuard><Login /></LoginGuard>} />
            <Route path="/" element={<AuthGuard><Index /></AuthGuard>} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
