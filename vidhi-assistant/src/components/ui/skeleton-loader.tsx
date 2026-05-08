import { motion } from "framer-motion";

interface SkeletonLoaderProps {
  variant?: "text" | "message" | "card" | "list";
  count?: number;
}

export const SkeletonLoader = ({ variant = "text", count = 1 }: SkeletonLoaderProps) => {
  const shimmer = {
    initial: { backgroundPosition: "-200% 0" },
    animate: {
      backgroundPosition: "200% 0",
      transition: {
        repeat: Infinity,
        duration: 1.5,
        ease: "linear"
      }
    }
  };

  const baseClass = "bg-gradient-to-r from-muted via-muted/50 to-muted bg-[length:200%_100%] rounded-lg";

  if (variant === "message") {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <motion.div
              className={`${baseClass} w-10 h-10 rounded-full flex-shrink-0`}
              {...shimmer}
            />
            <div className="flex-1 space-y-2">
              <motion.div className={`${baseClass} h-4 w-3/4`} {...shimmer} />
              <motion.div className={`${baseClass} h-4 w-full`} {...shimmer} />
              <motion.div className={`${baseClass} h-4 w-5/6`} {...shimmer} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="border border-border rounded-xl p-4 space-y-3">
            <motion.div className={`${baseClass} h-6 w-1/3`} {...shimmer} />
            <motion.div className={`${baseClass} h-4 w-full`} {...shimmer} />
            <motion.div className={`${baseClass} h-4 w-5/6`} {...shimmer} />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div className="space-y-2">
        {Array.from({ length: count }).map((_, i) => (
          <motion.div key={i} className={`${baseClass} h-12 w-full`} {...shimmer} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div key={i} className={`${baseClass} h-4 w-full`} {...shimmer} />
      ))}
    </div>
  );
};
