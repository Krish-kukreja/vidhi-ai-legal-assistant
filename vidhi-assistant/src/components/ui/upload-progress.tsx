import { motion } from "framer-motion";
import { FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

export interface UploadFile {
  name: string;
  size: number;
  progress: number; // 0-100
  status: "pending" | "uploading" | "success" | "error";
  error?: string;
}

interface UploadProgressProps {
  files: UploadFile[];
  onCancel?: (fileName: string) => void;
}

export const UploadProgress = ({ files, onCancel }: UploadProgressProps) => {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-2">
      {files.map((file, index) => (
        <motion.div
          key={`${file.name}-${index}`}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="border border-border rounded-lg p-3 bg-card"
        >
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0">
              {file.status === "uploading" && (
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              )}
              {file.status === "success" && (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              )}
              {file.status === "error" && (
                <AlertCircle className="h-5 w-5 text-destructive" />
              )}
              {file.status === "pending" && (
                <FileText className="h-5 w-5 text-muted-foreground" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-1">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatFileSize(file.size)}
                </span>
              </div>

              {file.status === "uploading" && (
                <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${file.progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              )}

              {file.status === "error" && file.error && (
                <p className="text-xs text-destructive mt-1">{file.error}</p>
              )}

              {file.status === "success" && (
                <p className="text-xs text-green-600 dark:text-green-500 mt-1">
                  Upload complete
                </p>
              )}
            </div>

            {file.status === "uploading" && onCancel && (
              <button
                onClick={() => onCancel(file.name)}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
};
