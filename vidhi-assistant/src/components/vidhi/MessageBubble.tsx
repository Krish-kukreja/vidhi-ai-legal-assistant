import { Play, Square, Volume2, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { INDIAN_LANGUAGES, type LanguageConfig } from "@/config/languages";

export interface Message {
  id: string;
  text: string;
  sender: "user" | "ai";
  language?: string;
  timestamp: Date;
  audioUrl?: string; // Kept for backend polly compat if needed
}

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.sender === "user";
  const [isSpeaking, setIsSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Get language configuration
  const languageKey = message.language?.toLowerCase() || "english";
  const languageConfig: LanguageConfig = INDIAN_LANGUAGES[languageKey] || INDIAN_LANGUAGES.english;

  const handlePlayback = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(message.text.replace(/[⚖️🏛️📄🙏🎤]/g, ""));
    utteranceRef.current = utterance;

    // Use BCP 47 language tag from configuration
    utterance.lang = languageConfig.bcp47;
    utterance.rate = 0.9;

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <motion.div
      className={`flex w-full mb-6 ${isUser ? "justify-end" : "justify-start"}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={`flex max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>

        {!isUser && (
          <div className="flex-shrink-0 mr-4 mt-1">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
          </div>
        )}

        <div className="flex flex-col w-full">
          <div
            className={`px-4 py-3 ${isUser
              ? "bg-chat-user text-chat-user-foreground rounded-3xl rounded-tr-md inline-block whitespace-pre-wrap text-[15px]"
              : "bg-chat-ai text-chat-ai-foreground max-w-none text-[15px] leading-relaxed"
              }`}
          >
            {!isUser ? (
              <ReactMarkdown>{message.text}</ReactMarkdown>
            ) : (
              message.text
            )}
          </div>

          {/* Controls Bar */}
          <div className={`flex items-center gap-3 mt-2 ${isUser ? "justify-end mr-2" : "justify-start ml-2"}`}>
            <button
              onClick={handlePlayback}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              aria-label={isSpeaking ? "Stop playback" : "Listen to message"}
            >
              {isSpeaking ? <Square className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
              {isSpeaking ? "Stop" : languageConfig.name}
            </button>
            <span className="text-[10px] text-muted-foreground/60">
              {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>

      </div>
    </motion.div>
  );
};

export default MessageBubble;
