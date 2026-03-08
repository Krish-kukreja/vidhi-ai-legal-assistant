import { useState, useRef, useEffect } from "react";
import { Send, Mic, Paperclip, X, Languages, Check } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import AudioWave from "./AudioWave";
import { toast } from "@/hooks/use-toast";
import { INDIAN_LANGUAGES, type LanguageConfig } from "@/config/languages";

interface ChatInputProps {
  onSend: (text: string, language?: string, file?: File) => void;
}

// TypeScript interfaces for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

const ChatInput = ({ onSend }: ChatInputProps) => {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingComplete, setRecordingComplete] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("hindi");
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const languageMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  // Close language menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (languageMenuRef.current && !languageMenuRef.current.contains(event.target as Node)) {
        setShowLanguageMenu(false);
      }
    };

    if (showLanguageMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showLanguageMenu]);

  const currentLanguage: LanguageConfig = INDIAN_LANGUAGES[selectedLanguage];

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && !selectedFile) return;

    if (selectedFile || trimmed) {
      const finalMsgText = trimmed || `Can you please analyze this file: ${selectedFile?.name}?`;
      onSend(finalMsgText, selectedLanguage, selectedFile || undefined);
    }

    setText("");
    setSelectedFile(null);
    setRecordingComplete(false);
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const startRecording = async () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast({
        title: "Not supported",
        description: "Speech recognition is not supported in your browser. Please use Chrome or Edge.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Request mic permission explicitly
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      toast({
        title: "Microphone access denied",
        description: "Please allow microphone access in your browser settings to use voice input.",
        variant: "destructive",
      });
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = currentLanguage.bcp47; // Use selected language
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let final = "";
      for (let i = 0; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      setTranscript(final + interim);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === "not-allowed") {
        toast({
          title: "Microphone access denied",
          description: "Please allow microphone access to use voice input.",
          variant: "destructive",
        });
      } else if (event.error === "language-not-supported") {
        toast({
          title: "Language not supported",
          description: `${currentLanguage.name} is not supported by your browser. Falling back to Hindi.`,
          variant: "destructive",
        });
        setSelectedLanguage("hindi");
      }
      setIsRecording(false);
      setTranscript("");
    };

    recognition.onend = () => {
      // If still recording, it ended naturally
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
    setTranscript("");
    setIsRecording(true);
    recognition.start();
  };

  const stopRecording = () => {
    recognitionRef.current?.stop();
    setIsRecording(false);

    // Don't auto-send, let user review and edit
    if (transcript.trim()) {
      setText(transcript.trim());
      setRecordingComplete(true);
      toast({
        title: "Recording Complete",
        description: "Review your message and click send, or continue editing.",
      });
    }
    setTranscript("");
  };

  const cancelRecording = () => {
    recognitionRef.current?.abort();
    setIsRecording(false);
    setTranscript("");
    setRecordingComplete(false);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file type
    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/jpg",
      "image/png",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload PDF, Word, or image files only.",
        variant: "destructive",
      });
      return;
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Please upload files smaller than 10MB.",
        variant: "destructive",
      });
      return;
    }

    setSelectedFile(file);
    toast({
      title: "File selected",
      description: `${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
    });
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleLanguageSelect = (languageKey: string) => {
    setSelectedLanguage(languageKey);
    setShowLanguageMenu(false);
    toast({
      title: "Language changed",
      description: `Now using ${INDIAN_LANGUAGES[languageKey].name} (${INDIAN_LANGUAGES[languageKey].nativeName})`,
    });
  };

  // Group languages by support level for better UX
  const awsSupportedLanguages = Object.entries(INDIAN_LANGUAGES).filter(
    ([_, lang]) => lang.awsTranscribeSupported && lang.awsPollySupported
  );
  const bhashiniLanguages = Object.entries(INDIAN_LANGUAGES).filter(
    ([_, lang]) => lang.bhashiniSupported && !lang.awsTranscribeSupported
  );
  const otherLanguages = Object.entries(INDIAN_LANGUAGES).filter(
    ([_, lang]) => !lang.awsTranscribeSupported && !lang.bhashiniSupported
  );

  return (
    <div className="bg-background px-4 py-3 relative w-full">
      <AnimatePresence>
        {isRecording && (
          <motion.div
            className="flex flex-col gap-2 py-3 mb-3 rounded-2xl bg-sos/5 border border-sos/20 px-4"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="flex items-center justify-center gap-4">
              <div className="w-3 h-3 rounded-full bg-sos animate-pulse" />
              <AudioWave />
              <span className="text-sm font-medium text-foreground">
                Listening in {currentLanguage.name}...
              </span>
              <button
                onClick={cancelRecording}
                className="p-1.5 rounded-full hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
            {transcript && (
              <p className="text-sm text-muted-foreground text-center italic">"{transcript}"</p>
            )}
            <div className="flex items-center justify-center gap-2 mt-2">
              <button
                onClick={stopRecording}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                <Check className="h-4 w-4" />
                Done Recording
              </button>
            </div>
          </motion.div>
        )}

        {recordingComplete && !isRecording && (
          <motion.div
            className="py-2 mb-2 px-3 rounded-lg bg-green-500/10 border border-green-500/20"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
              <Check className="h-4 w-4" />
              <span>Recording complete! Review and edit your message below, then click send.</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="w-full bg-muted rounded-[24px] flex flex-col pt-2 pb-2 px-2 transition-all border border-transparent focus-within:border-border/50 shadow-sm relative">

        {/* Top Controls Row inside the Input Box */}
        <div className="flex items-center justify-between px-2 pb-1">
          {/* File Thumbnail Area */}
          <div className="flex">
            <AnimatePresence>
              {selectedFile && (
                <motion.div
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-background border border-border/50 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                >
                  <Paperclip className="h-3.5 w-3.5 text-primary" />
                  <span className="text-xs font-medium text-foreground max-w-[120px] truncate">{selectedFile.name}</span>
                  <button
                    onClick={removeFile}
                    className="p-0.5 rounded-full hover:bg-muted transition-colors ml-1"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Language Selector (Top Right inside box) */}
          <div className="relative z-50 flex justify-end" ref={languageMenuRef}>
            <button
              onClick={() => setShowLanguageMenu(!showLanguageMenu)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-muted-foreground hover:text-foreground h-8"
              aria-label="Select language"
              title={`Speech/Text Input: ${currentLanguage.name}`}
            >
              <Languages className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">{currentLanguage.name}</span>
            </button>

            <AnimatePresence>
              {showLanguageMenu && (
                <motion.div
                  className="absolute bottom-full right-0 mb-2 w-64 max-h-80 overflow-y-auto bg-popover border border-border rounded-xl shadow-lg"
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  style={{ transformOrigin: "bottom right" }}
                >
                  <div className="p-2 border-b border-border sticky top-0 bg-popover/90 backdrop-blur-sm z-10">
                    <h3 className="font-semibold text-xs text-foreground px-2">Input Language</h3>
                  </div>

                  <div className="p-1.5">
                    {Object.entries(INDIAN_LANGUAGES).map(([key, lang]) => (
                      <button
                        key={key}
                        onClick={() => handleLanguageSelect(key)}
                        className={`w-full text-left px-3 py-2 rounded-md hover:bg-muted transition-colors flex items-center justify-between group ${selectedLanguage === key ? "bg-primary/10 text-primary font-medium" : "text-foreground"
                          }`}
                      >
                        <span className="text-sm">{lang.name}</span>
                        {selectedLanguage === key && (
                          <Check className="h-3.5 w-3.5" />
                        )}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Text Input Row */}
        <div className="flex items-end gap-2 px-2 pb-1">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-muted-foreground hover:text-foreground h-10 w-10 flex items-center justify-center shrink-0 mb-0.5"
            aria-label="Attach file"
          >
            <Paperclip className="h-5 w-5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            onChange={handleFileSelect}
            className="hidden"
          />

          <textarea
            ref={inputRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a legal question...`}
            className="flex-1 bg-transparent py-3 mb-0.5 text-[15px] resize-none outline-none text-foreground placeholder:text-muted-foreground/70 max-h-[120px] min-h-[44px]"
            rows={1}
            style={{ paddingLeft: '8px' }}
          />

          {text.trim() || selectedFile ? (
            <motion.button
              onClick={handleSend}
              className="p-2 rounded-full bg-primary text-primary-foreground h-10 w-10 flex items-center justify-center shrink-0 mb-0.5 shadow-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              aria-label="Send"
            >
              <Send className="h-4 w-4 ml-0.5" />
            </motion.button>
          ) : (
            <motion.button
              onClick={toggleRecording}
              className={`p-2 rounded-full h-10 w-10 flex items-center justify-center shrink-0 mb-0.5 transition-colors ${isRecording
                ? "bg-sos text-sos-foreground animate-pulse"
                : "bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-foreground"
                }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              aria-label={isRecording ? "Stop recording" : "Tap to speak"}
            >
              <Mic className="h-5 w-5" />
            </motion.button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
