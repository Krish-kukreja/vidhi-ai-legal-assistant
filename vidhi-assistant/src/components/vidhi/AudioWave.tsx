import { motion } from "framer-motion";

const AudioWave = () => {
  const bars = 5;
  return (
    <div className="flex items-center gap-1 h-6">
      {Array.from({ length: bars }).map((_, i) => (
        <motion.div
          key={i}
          className="w-1 rounded-full bg-accent"
          animate={{ height: [4, 20, 4] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
};

export default AudioWave;
