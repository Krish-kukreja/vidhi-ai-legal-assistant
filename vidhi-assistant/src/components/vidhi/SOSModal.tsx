import { X, ShieldAlert } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ScrollArea } from "@/components/ui/scroll-area";

const rights = [
  { title: "Right to Remain Silent", desc: "You are not obligated to answer any questions beyond your name and address." },
  { title: "Demand an Arrest Memo", desc: "Under D.K. Basu guidelines, police must provide a signed arrest memo with date and time." },
  { title: "Right to a Lawyer", desc: "You have the right to consult a lawyer of your choice immediately upon arrest." },
  { title: "Right to Inform Family", desc: "Police must inform a family member or friend about your arrest and location." },
  { title: "No Torture or Coercion", desc: "You cannot be subjected to any form of physical or mental torture." },
  { title: "Right to Medical Examination", desc: "You must be medically examined within 48 hours of arrest." },
];

interface SOSModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SOSModal = ({ isOpen, onClose }: SOSModalProps) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-foreground/60 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            className="relative z-10 w-full max-w-lg max-h-[85vh] rounded-2xl bg-card border-2 border-sos shadow-2xl flex flex-col overflow-hidden"
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
          >
            <div className="bg-sos px-6 py-4 shrink-0 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldAlert className="h-7 w-7 text-sos-foreground" />
                <h2 className="text-xl font-bold text-sos-foreground">Your Emergency Rights</h2>
              </div>
              <button onClick={onClose} className="text-sos-foreground/80 hover:text-sos-foreground transition-colors">
                <X className="h-6 w-6" />
              </button>
            </div>

            <ScrollArea className="h-[60vh] w-full pr-4">
              <div className="p-6 pr-2 space-y-4">
                <p className="text-sm text-muted-foreground font-medium">
                  If detained by police, you have these fundamental rights under Indian law:
                </p>
                {rights.map((right, i) => (
                  <motion.div
                    key={i}
                    className="rounded-xl bg-sos/5 border border-sos/20 p-4"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08 }}
                  >
                    <h3 className="font-bold text-foreground text-lg flex items-center gap-2">
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-sos text-sos-foreground text-sm font-bold shrink-0">
                        {i + 1}
                      </span>
                      {right.title}
                    </h3>
                    <p className="text-muted-foreground mt-1 ml-9 text-sm leading-relaxed">{right.desc}</p>
                  </motion.div>
                ))}
              </div>
            </ScrollArea>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SOSModal;
