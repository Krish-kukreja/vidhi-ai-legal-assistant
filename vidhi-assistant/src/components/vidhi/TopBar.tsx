import { Menu, ShieldAlert, Scale, User, LogOut } from "lucide-react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

interface TopBarProps {
  onMenuClick: () => void;
  onSOSClick: () => void;
}

const TopBar = ({ onMenuClick, onSOSClick }: TopBarProps) => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user is authenticated
    const auth = localStorage.getItem("vidhi_auth");
    setIsAuthenticated(!!auth);
  }, []);

  const handleAuthClick = () => {
    if (isAuthenticated) {
      // Logout
      localStorage.removeItem("vidhi_auth");
      setIsAuthenticated(false);
      navigate("/login");
    } else {
      // Go to login
      navigate("/login");
    }
  };

  return (
    <header className="sticky top-0 z-20 bg-card/80 backdrop-blur-xl border-b border-border">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-xl hover:bg-muted transition-colors"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5 text-foreground" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 flex items-center justify-center">
              <img src="/logo.png" alt="Vidhi Logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground leading-none">VIDHI</h1>
              <p className="text-[10px] text-muted-foreground font-medium">Voice-Integrated Legal Aid</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const root = window.document.documentElement;
              const isDark = root.classList.contains("dark");
              if (isDark) {
                root.classList.remove("dark");
                localStorage.setItem("vidhi_theme", "light");
              } else {
                root.classList.add("dark");
                localStorage.setItem("vidhi_theme", "dark");
              }
            }}
            className="p-2 rounded-xl hover:bg-muted transition-colors"
            aria-label="Toggle theme"
            title="Toggle Theme"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-foreground"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></svg>
          </button>

          <button
            onClick={handleAuthClick}
            className="p-2 rounded-xl hover:bg-muted transition-colors"
            aria-label={isAuthenticated ? "Logout" : "Login"}
            title={isAuthenticated ? "Logout" : "Login"}
          >
            {isAuthenticated ? (
              <LogOut className="h-5 w-5 text-foreground" />
            ) : (
              <User className="h-5 w-5 text-foreground" />
            )}
          </button>

          <motion.button
            onClick={onSOSClick}
            className="flex items-center gap-2 bg-sos text-sos-foreground px-4 py-2.5 rounded-xl font-bold text-sm shadow-lg shadow-sos/30 hover:shadow-sos/50 transition-shadow"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Emergency SOS"
          >
            <ShieldAlert className="h-5 w-5" />
            <span className="hidden sm:inline">SOS</span>
            <span className="sm:hidden">SOS</span>
          </motion.button>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
