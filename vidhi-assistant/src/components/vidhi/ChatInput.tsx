import { useState, useRef, useEffect } from "react";
import { Send, Mic, Paperclip, X, Languages, Check, Square } from "lucide-react";

import { motion, AnimatePresence } from "framer-motion";
import AudioWave from "./AudioWave";
import { toast } from "@/hooks/use-toast";
import { INDIAN_LANGUAGES, type LanguageConfig } from "@/config/languages";

interface ChatInputProps {
  onSend: (text: string, language?: string, files?: File[]) => void;
  isLoading?: boolean;
  onStop?: () => void;
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

const ChatInput = ({ onSend, isLoading = false, onStop }: ChatInputProps) => {

  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingComplete, setRecordingComplete] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("hindi");
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const languageMenuRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isCancelledRef = useRef<boolean>(false);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
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
    if (!trimmed && selectedFiles.length === 0) return;

    if (selectedFiles.length > 0 || trimmed) {
      const finalMsgText = trimmed || `Can you please analyze these files: ${selectedFiles.map(f => f.name).join(', ')}?`;
      onSend(finalMsgText, selectedLanguage, selectedFiles.length > 0 ? selectedFiles : undefined);
    }

    setText("");
    setSelectedFiles([]);
    setRecordingComplete(false);
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading) handleSend();
    }
  };


  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const startMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Detect the best supported audio format for this browser
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
        'audio/mp4',
      ].find(type => MediaRecorder.isTypeSupported(type)) || '';

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];
      isCancelledRef.current = false;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
        if (!isCancelledRef.current) {
          const actualMime = mediaRecorder.mimeType || 'audio/webm';
          // Map MIME type to file extension
          const ext = actualMime.includes('ogg') ? 'ogg'
            : actualMime.includes('mp4') ? 'mp4'
              : 'webm';
          const audioBlob = new Blob(audioChunksRef.current, { type: actualMime });
          const audioFile = new File([audioBlob], `voice_message.${ext}`, { type: actualMime });

          // Wait briefly for any final SpeechRecognition results to settle in the React state
          setTimeout(() => {
            const currentText = inputRef.current?.value || "";
            // If we have transcribed text from the browser STT, we don't need to send the audio file 
            // to be re-transcribed (prevents 10s AWS Transcribe delay).
            // If text is empty (Web Speech API failed/unsupported), we MUST send the audio file to fallback to AWS.
            if (currentText.trim()) {
              onSend(currentText, selectedLanguage, []);
            } else {
              console.log("Sending fallback audio file to backend:", audioFile);
              toast({
                title: "Voice sent",
                description: "Audio captured. Processing with AWS Transcribe...",
              });
              onSend("", selectedLanguage, [audioFile]);
            }
            setText("");
          }, 150);
        }
        audioChunksRef.current = [];
        setIsRecording(false);
      };

      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      mediaRecorder.start(1000); // collect chunks every second

    } catch (err) {
      console.error("Microphone access error:", err);
      // Give the user explicit instructions on how to fix the permission issue
      toast({
        title: "Microphone Access Denied",
        description: "Please click the lock icon 🔒 in your browser's address bar, find 'Microphone', and change it to 'Allow'. Then refresh the page.",
        variant: "destructive",
        duration: 8000,
      });
    }
  };


  const startRecording = () => {
    // ALWAYS start MediaRecorder as a fallback (and to control recording state)
    startMediaRecorder();

    // Try to use browser's built-in speech recognition for instant results
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = currentLanguage.bcp47 || 'hi-IN';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognitionRef.current = recognition;
      isCancelledRef.current = false;
      let currentFinal = "";
      // Save existing text before recording starts
      const initialText = text;

      recognition.onstart = () => {
        setTranscript("");
      };

      recognition.onresult = (event: any) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            currentFinal += event.results[i][0].transcript + " ";
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        const fullTranscript = (currentFinal + interim).trim();
        setTranscript(fullTranscript);
        // Append transcribed text to the initial text with a space
        const newText = initialText ? `${initialText} ${fullTranscript}` : fullTranscript;
        setText(newText); // Live update the textarea
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
      };

      recognition.onend = () => {
        // Sending is handled by mediaRecorder.onstop
      };

      try {
        recognition.start();
      } catch (e) {
        console.error('Browser STT failed to start', e);
      }
    }
  };


  const stopRecording = () => {
    isCancelledRef.current = false;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const cancelRecording = () => {
    isCancelledRef.current = true;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }
    setText(""); // Clear text if cancelled
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/jpg",
      "image/png",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    const validFiles = files.filter(file => {
      if (!allowedTypes.includes(file.type)) {
        toast({
          title: "Invalid file type",
          description: `${file.name} is not a supported file type.`,
          variant: "destructive",
        });
        return false;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: `${file.name} is larger than 10MB.`,
          variant: "destructive",
        });
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...validFiles]);
      toast({
        title: "Files selected",
        description: `Added ${validFiles.length} file(s)`,
      });
    }
  };

  const removeFile = (indexToRemove: number) => {
    setSelectedFiles(prev => prev.filter((_, index) => index !== indexToRemove));
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
              <span className="text-sm font-medium text-foreground truncate max-w-[200px]">
                {transcript || `Listening in ${currentLanguage.name}...`}
              </span>
              <button
                onClick={cancelRecording}
                className="p-1.5 rounded-full hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
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
      </AnimatePresence>

      <div className="w-full bg-muted rounded-[24px] flex flex-col pt-2 pb-2 px-2 transition-all border border-transparent focus-within:border-border/50 shadow-sm relative">

        {/* Top Controls Row inside the Input Box */}
        <div className="flex items-center justify-between px-2 pb-1">
          <div className="flex flex-wrap gap-2 mb-2">
            <AnimatePresence>
              {selectedFiles.map((file, index) => (
                <motion.div
                  key={`${file.name}-${index}`}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-background border border-border/50 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                >
                  <Paperclip className="h-3.5 w-3.5 text-primary" />
                  <span className="text-xs font-medium text-foreground max-w-[120px] truncate">{file.name}</span>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-0.5 rounded-full hover:bg-muted transition-colors ml-1"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </motion.div>
              ))}
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
            multiple
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            onChange={handleFileSelect}
            className="hidden"
          />


          <textarea
            ref={inputRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? "Vidhi is thinking..." : `Ask a legal question...`}
            disabled={isLoading}
            className={`flex-1 bg-transparent py-3 mb-0.5 text-[15px] resize-none outline-none text-foreground placeholder:text-muted-foreground/70 max-h-[120px] min-h-[44px] transition-opacity ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            rows={1}
            style={{ paddingLeft: '8px' }}
          />


          {isLoading ? (
            // Stop / Cancel button while AI is generating
            <motion.button
              onClick={onStop}
              className="p-2 rounded-full bg-destructive text-destructive-foreground h-10 w-10 flex items-center justify-center shrink-0 mb-0.5 shadow-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              animate={{ opacity: [1, 0.6, 1] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
              aria-label="Stop generating"
              title="Stop generating"
            >
              <Square className="h-4 w-4 fill-current" />
            </motion.button>
          ) : text.trim() || selectedFiles.length > 0 ? (
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
