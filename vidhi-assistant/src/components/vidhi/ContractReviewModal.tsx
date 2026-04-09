import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { AlertTriangle, CheckCircle, FileText } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "@/hooks/use-toast";

interface ContractReviewModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const ContractReviewModal = ({ isOpen, onClose }: ContractReviewModalProps) => {
    const [contractText, setContractText] = useState("");
    const [playbookRules, setPlaybookRules] = useState("Minimize liability. Ensure governing law is India.");
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<any>(null);

    const handleReview = async () => {
        if (!contractText) {
            toast({ title: "Error", description: "Please paste a contract.", variant: "destructive" });
            return;
        }

        setIsLoading(true);
        setResults(null);
        try {
            const res = await fetch("http://localhost:8000/api/v1/contracts/review", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ document_text: contractText, playbook_rules: playbookRules })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            setResults(data.data);
            toast({ title: "Review Complete", description: "Contract analysis loaded." });
        } catch (e: any) {
            toast({ title: "Review Failed", description: e.message, variant: "destructive" });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] min-h-[60vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>AI Contract Review & Redlining</DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-hidden grid lg:grid-cols-2 gap-4">
                    <div className="flex flex-col space-y-4 border-r pr-4 pt-2">
                        <div className="space-y-2 flex-1 flex flex-col">
                            <Label>Contract Text</Label>
                            <Textarea
                                value={contractText}
                                onChange={e => setContractText(e.target.value)}
                                placeholder="Paste the contract text here..."
                                className="flex-1 resize-none"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Playbook Rules</Label>
                            <Input
                                value={playbookRules}
                                onChange={e => setPlaybookRules(e.target.value)}
                                placeholder="e.g. Neutral governing law, max 30 day payment terms"
                            />
                        </div>
                        <Button onClick={handleReview} disabled={isLoading} className="w-full">
                            {isLoading ? "Analyzing..." : "Review Contract"}
                        </Button>
                    </div>

                    <ScrollArea className="flex-1 pl-2">
                        {results ? (
                            <div className="space-y-4 pt-2 pr-4">
                                {results.redlines.map((red: any, idx: number) => (
                                    <div key={idx} className={`p-4 border rounded-md border-l-4 ${red.severity === 'high' ? 'border-l-red-500 bg-red-500/10' : red.severity === 'medium' ? 'border-l-yellow-500 bg-yellow-500/10' : 'border-l-green-500 bg-green-500/10'}`}>
                                        <h4 className="font-semibold text-sm flex items-center gap-2 mb-2">
                                            {red.severity === 'high' ? <AlertTriangle className="w-4 h-4 text-red-500" /> : <CheckCircle className="w-4 h-4 text-green-500" />}
                                            {red.severity.toUpperCase()} RISK
                                        </h4>
                                        <div className="text-sm space-y-2">
                                            <p><strong>Original Clause:</strong> <span className="line-through text-muted-foreground">{red.original_clause}</span></p>
                                            <p><strong>Suggested Redline:</strong> <span className="text-green-600 font-medium">{red.suggested_redline}</span></p>
                                            <div className="bg-background mt-2 p-2 rounded text-xs border border-border">
                                                <span className="font-semibold text-foreground">Reasoning: </span>
                                                <span className="text-muted-foreground">{red.reasoning}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center text-muted-foreground text-sm flex-col gap-3 py-10 opacity-70">
                                <FileText className="w-12 h-12" />
                                <p>Paste a contract and Playbook rules to see AI redlines.</p>
                            </div>
                        )}
                    </ScrollArea>
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default ContractReviewModal;
