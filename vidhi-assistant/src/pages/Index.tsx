import { useState, useRef, useEffect } from "react";
import TopBar from "@/components/vidhi/TopBar";
import ChatSidebar from "@/components/vidhi/ChatSidebar";
import QuickActions from "@/components/vidhi/QuickActions";
import ChatInput from "@/components/vidhi/ChatInput";
import MessageBubble, { Message } from "@/components/vidhi/MessageBubble";
import TypingIndicator from "@/components/vidhi/TypingIndicator";
import SOSModal from "@/components/vidhi/SOSModal";
import { updateLastActive, saveChatToHistory, getDisplayName, getChatHistory, updateChatDetails } from "@/utils/userStorage";
import { sendQuery } from "@/api/client";
import { INDIAN_LANGUAGES } from "@/config/languages";
import { toast } from "@/hooks/use-toast";

const Index = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sosOpen, setSOSOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSelectChat = (chatId: string) => {
    const history = getChatHistory();
    const chat = history.find(c => c.id === chatId);
    if (chat) {
      setActiveChatId(chatId);
      // Ensure timestamps are Date objects
      const loadedMessages = (chat.messages || []).map((m: any) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      }));
      setMessages(loadedMessages);
      setChatStarted(true);
      setSidebarOpen(false);
    }
  };

  const userName = getDisplayName().split(' ')[0];

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  };

  useEffect(scrollToBottom, [messages, isTyping]);

  // Update last active on mount
  useEffect(() => {
    updateLastActive();
  }, []);

  const handleNewChat = () => {
    setActiveChatId(null);
    setMessages([]);
    setChatStarted(false);
    setSidebarOpen(false);
  };

  const sendMessage = async (text: string, language?: string) => {
    const langKey = language || "hindi";
    const userMsg: Message = {
      id: Date.now().toString(),
      text,
      sender: "user",
      language: langKey,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    // Mark chat as started
    if (!chatStarted) {
      setChatStarted(true);
    }

    try {
      const languageConfig = INDIAN_LANGUAGES[langKey] || INDIAN_LANGUAGES.hindi;

      const response = await sendQuery({
        text: text,
        language: languageConfig.name,
        language_code: languageConfig.bcp47,
        use_aws_stt: false
      });

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response,
        sender: "ai",
        language: langKey,
        timestamp: new Date(),
        audioUrl: response.audio_url
      };

      setMessages((prev) => {
        const newMessages = [...prev, aiMsg];

        // Save to chat history after the first complete exchange (1 user msg + 1 ai msg)
        // If it's a new chat, create it. If it exists, update it.
        if (newMessages.length === 2 && !activeChatId) {
          const firstUserMessage = newMessages.find(m => m.sender === "user");
          if (firstUserMessage) {
            const newChat = saveChatToHistory(firstUserMessage.text, newMessages);
            setActiveChatId(newChat.id);
          }
        } else if (activeChatId) {
          updateChatDetails(activeChatId, {
            messageCount: newMessages.length,
            messages: newMessages
          });
        }

        return newMessages;
      });

      // If there's an audio URL from AWS Polly, play it!
      if (response.audio_url) {
        const audio = new Audio(response.audio_url);
        audio.play().catch(e => console.error("Could not auto-play audio", e));
      }

    } catch (error: any) {
      console.error("Chat error:", error);
      toast({
        title: "Connection Error",
        description: "Could not connect to the backend AI server. Is it running?",
        variant: "destructive"
      });

      // Add error message to chat
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I am having trouble connecting to my AI backend. Please ensure the backend server is running on port 8000.",
        sender: "ai",
        language: "english",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
      updateLastActive();
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <ChatSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onMenuClick={() => setSidebarOpen(true)} onSOSClick={() => setSOSOpen(true)} />

        <div ref={scrollRef} className="flex-1 overflow-y-auto w-full flex flex-col items-center">
          {messages.length === 0 ? (
            <div className="flex-1 w-full max-w-4xl px-4 flex flex-col items-center justify-center min-h-[50vh]">
              <div className="w-full text-left md:mb-12 mb-6 mt-16">
                <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-2 text-transparent bg-clip-text bg-gradient-to-r from-primary/80 to-primary/40">
                  Hello, {userName}
                </h1>
                <p className="text-3xl md:text-4xl font-medium text-muted-foreground/60 w-full animate-pulse-slow">
                  How can I help you today?
                </p>
              </div>
            </div>
          ) : (
            <div className="w-full max-w-4xl px-4 py-8 space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isTyping && <TypingIndicator />}
            </div>
          )}
        </div>

        <div className="w-full max-w-4xl mx-auto px-4 pb-4">
          {messages.length === 0 && (
            <div className="mb-4">
              <QuickActions onAction={sendMessage} />
            </div>
          )}
          <ChatInput onSend={sendMessage} />
          <div className="text-center mt-3 text-xs text-muted-foreground">
            VIDHI may display inaccurate info, including about people, so double-check its responses.
          </div>
        </div>
      </div>

      <SOSModal isOpen={sosOpen} onClose={() => setSOSOpen(false)} />
    </div>
  );
};

export default Index;
