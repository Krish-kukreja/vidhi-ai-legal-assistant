import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, AlertTriangle } from "lucide-react";

interface TimeoutWarningProps {
  isLoading: boolean;
  warningThreshold?: number; // milliseconds
  criticalThreshold?: number; // milliseconds
  onTimeout?: () => void;
}

export const TimeoutWarning = ({
  isLoading,
  warningThreshold = 10000, // 10 seconds
  criticalThreshold = 30000, // 30 seconds
  onTimeout
}: TimeoutWarningProps) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showWarning, setShowWarning] = useState(false);
  const [isCritical, setIsCritical] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setElapsedTime(0);
      setShowWarning(false);
      setIsCritical(false);
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setElapsedTime(elapsed);

      if (elapsed >= criticalThreshold) {
        setIsCritical(true);
        setShowWarning(true);
        if (onTimeout) onTimeout();
      } else if (elapsed >= warningThreshold) {
        setShowWarning(true);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isLoading, warningThreshold, criticalThreshold, onTimeout]);

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    return `${seconds}s`;
  };

  return (
    <AnimatePresence>
      {showWarning && isLoading && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isCritical
              ? "bg-destructive/10 border-destructive/30 text-destructive"
              : "bg-yellow-500/10 border-yellow-500/30 text-yellow-600 dark:text-yellow-500"
          }`}
        >
          {isCritical ? (
            <AlertTriangle className="h-4 w-4 animate-pulse" />
          ) : (
            <Clock className="h-4 w-4" />
          )}
          <span className="text-sm font-medium">
            {isCritical
              ? `Taking longer than expected (${formatTime(elapsedTime)})`
              : `This is taking a while (${formatTime(elapsedTime)})`}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
