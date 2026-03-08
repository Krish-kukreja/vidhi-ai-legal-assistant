import { Scale, Landmark, FileSearch } from "lucide-react";
import { motion } from "framer-motion";

const actions = [
  {
    icon: Scale,
    label: "Know My Rights",
    desc: "Police & legal emergencies",
    gradient: "from-primary to-primary/80",
  },
  {
    icon: Landmark,
    label: "Find Gov Schemes",
    desc: "Subsidies & financial aid",
    gradient: "from-success to-success/80",
  },
  {
    icon: FileSearch,
    label: "Scan a Document",
    desc: "Contract & legal analysis",
    gradient: "from-accent to-accent/80",
  },
];

interface QuickActionsProps {
  onAction: (label: string) => void;
}

const QuickActions = ({ onAction }: QuickActionsProps) => {
  return (
    <div className="grid grid-cols-3 gap-3 px-4 py-3">
      {actions.map((action, i) => (
        <motion.button
          key={action.label}
          onClick={() => onAction(action.label)}
          className={`flex flex-col items-center gap-2 rounded-2xl bg-gradient-to-br ${action.gradient} p-4 text-primary-foreground shadow-lg hover:shadow-xl transition-shadow`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          <action.icon className="h-7 w-7" />
          <span className="text-xs sm:text-sm font-semibold text-center leading-tight">{action.label}</span>
          <span className="text-[10px] sm:text-xs opacity-80 text-center hidden sm:block">{action.desc}</span>
        </motion.button>
      ))}
    </div>
  );
};

export default QuickActions;
