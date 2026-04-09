import { Scale, Landmark, FileSearch, PenTool } from "lucide-react";
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
  {
    icon: PenTool,
    label: "Draft Legal Document",
    desc: "Generate custom legal drafts",
    gradient: "from-blue-500 to-blue-500/80",
  },
];

interface QuickActionsProps {
  onAction: (label: string) => void;
}

const QuickActions = ({ onAction }: QuickActionsProps) => {
  return (
    <div className="flex flex-wrap justify-start gap-3 px-4 max-w-3xl mx-auto mb-4">
      {actions.map((action, i) => (
        <motion.button
          key={action.label}
          onClick={() => onAction(action.label)}
          className="flex items-center gap-3 rounded-2xl bg-muted/50 hover:bg-muted p-4 pr-6 transition-colors border border-transparent hover:border-border cursor-pointer min-w-[160px]"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
        >
          <action.icon className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground text-left">{action.label}</span>
        </motion.button>
      ))}
    </div>
  );
};

export default QuickActions;
