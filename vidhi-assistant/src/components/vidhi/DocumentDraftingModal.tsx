import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, Loader2, Download, CheckCircle2 } from "lucide-react";
import { draftDocument } from "@/api/client";
import { toast } from "@/hooks/use-toast";
import ReactMarkdown from "react-markdown";

interface DocumentDraftingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const DocumentDraftingModal = ({ isOpen, onClose }: DocumentDraftingModalProps) => {
    const [step, setStep] = useState<"input" | "loading" | "result">("input");

    const [docType, setDocType] = useState("");
    const [parties, setParties] = useState("");
    const [keyTerms, setKeyTerms] = useState("");

    const [draftResult, setDraftResult] = useState<{
        markdown: string;
        downloadUrl: string;
    } | null>(null);

    const handleDraft = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!docType || !parties || !keyTerms) {
            toast({ title: "Error", description: "Please fill all fields", variant: "destructive" });
            return;
        }

        setStep("loading");
        try {
            const response = await draftDocument({
                document_type: docType,
                parties: parties,
                key_terms: keyTerms,
            });

            if (response.success) {
                setDraftResult({
                    markdown: response.markdown_draft,
                    downloadUrl: response.download_url,
                });
                setStep("result");
                toast({ title: "Success", description: "Legal document drafted successfully." });
            } else {
                throw new Error("Failed to generate document.");
            }
        } catch (err: any) {
            toast({ title: "Error", description: err.message || "Failed to generate document", variant: "destructive" });
            setStep("input");
        }
    };

    const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

    const handleDownload = () => {
        if (draftResult?.downloadUrl) {
            window.open(`${API_BASE_URL}${draftResult.downloadUrl}`, '_blank');
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    className="bg-card w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-border"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-border bg-muted/30">
                        <div className="flex items-center gap-3">
                            <div className="bg-primary/10 p-2 rounded-xl">
                                <FileText className="w-6 h-6 text-primary" />
                            </div>
                            <h2 className="text-xl font-semibold tracking-tight">Draft Legal Document</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-muted rounded-full transition-colors"
                        >
                            <X className="w-5 h-5 text-muted-foreground" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {step === "input" && (
                            <form onSubmit={handleDraft} className="space-y-6 max-w-2xl mx-auto py-4">
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2 opacity-80">Document Type</label>
                                        <input
                                            type="text"
                                            className="flex h-12 w-full rounded-xl border border-input bg-background px-4 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                            placeholder="e.g. Non-Disclosure Agreement (NDA), Lease Agreement"
                                            value={docType}
                                            onChange={(e) => setDocType(e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2 opacity-80">Parties Involved</label>
                                        <input
                                            type="text"
                                            className="flex h-12 w-full rounded-xl border border-input bg-background px-4 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                            placeholder="e.g. Company A and Employee B"
                                            value={parties}
                                            onChange={(e) => setParties(e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2 opacity-80">Key Terms & Specifics</label>
                                        <textarea
                                            className="flex min-h-[120px] w-full rounded-xl border border-input bg-background px-4 py-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                                            placeholder="e.g. 2 years confidentiality, applies to all technical IP, jurisdiction is Mumbai courts."
                                            value={keyTerms}
                                            onChange={(e) => setKeyTerms(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center gap-2 rounded-xl border border-transparent font-medium transition-all"
                                >
                                    Generate Legal Draft
                                </button>
                            </form>
                        )}

                        {step === "loading" && (
                            <div className="h-full min-h-[400px] flex flex-col items-center justify-center space-y-6">
                                <div className="w-20 h-20 relative">
                                    <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                                    <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                                    <FileText className="absolute inset-0 m-auto w-8 h-8 text-primary animate-pulse" />
                                </div>
                                <div className="text-center space-y-2">
                                    <h3 className="text-lg font-medium">Retrieving Templates & Drafting...</h3>
                                    <p className="text-muted-foreground max-w-sm">
                                        VIDHI is retrieving the standard {docType || "document"} template and mapping your requirements using Bedrock ML models.
                                    </p>
                                </div>
                            </div>
                        )}

                        {step === "result" && draftResult && (
                            <div className="space-y-6">
                                <div className="flex items-center justify-between pb-4 border-b border-border">
                                    <div className="flex items-center gap-2 text-success">
                                        <CheckCircle2 className="w-5 h-5" />
                                        <span className="font-medium">Draft Generated Successfully</span>
                                    </div>
                                    <button
                                        onClick={handleDownload}
                                        className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-4 h-4" />
                                        Download DOCX
                                    </button>
                                </div>

                                <div className="prose prose-sm dark:prose-invert max-w-none bg-muted/30 p-6 rounded-xl border border-border overflow-y-auto max-h-[60vh]">
                                    <ReactMarkdown>{draftResult.markdown}</ReactMarkdown>
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
};

export default DocumentDraftingModal;
