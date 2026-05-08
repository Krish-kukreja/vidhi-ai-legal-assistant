import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

interface ProgressIndicatorProps {
  message?: string;
  progress?: number; // 0-100
  showSpinner?: boolean;
  variant?: "default" | "compact" | "inline";
}

export const ProgressIndicator = ({
  message = "Loading...",
  progress,
  showSpinner = true,
  variant = "default"
}: ProgressIndicatorProps) => {
  if (variant === "inline") {
    return (
      <div className="flex items-center gap-2">
        {showSpinner && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
        <span className="text-sm text-muted-foreground">{message}</span>
      </div>
    );
  }

  if (variant === "compact") {
    return (
      <div className="flex flex-col items-center gap-2 py-4">
        {showSpinner && <Loader2 className="h-6 w-6 animate-spin text-primary" />}
        <p className="text-sm text-muted-foreground">{message}</p>
        {progress !== undefined && (
          <div className="w-32 h-1 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 py-8">
      {showSpinner && (
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}
      <div className="text-center space-y-2">
        <p className="text-base font-medium text-foreground">{message}</p>
        {progress !== undefined && (
          <div className="w-64 h-2 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
