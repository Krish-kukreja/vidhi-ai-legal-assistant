import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { User, Phone, CreditCard, Calendar, MessageSquare, Clock, Shield } from "lucide-react";

interface UserData {
  name: string;
  authMethod: "guest" | "aadhaar" | "phone";
  identifier?: string;
  joinedDate: string;
  totalChats: number;
  lastActive: string;
}

interface ChatHistoryItem {
  id: string;
  title: string;
  date: string;
  messageCount: number;
}

interface UserProfileDialogProps {
  isOpen: boolean;
  onClose: () => void;
  userData: UserData;
  chatHistory: ChatHistoryItem[];
}

const UserProfileDialog = ({ isOpen, onClose, userData, chatHistory }: UserProfileDialogProps) => {
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const getAuthBadge = () => {
    switch (userData.authMethod) {
      case "aadhaar":
        return (
          <Badge variant="default" className="gap-1">
            <CreditCard className="h-3 w-3" />
            Aadhaar Verified
          </Badge>
        );
      case "phone":
        return (
          <Badge variant="secondary" className="gap-1">
            <Phone className="h-3 w-3" />
            Phone Verified
          </Badge>
        );
      case "guest":
        return (
          <Badge variant="outline" className="gap-1">
            <User className="h-3 w-3" />
            Guest User
          </Badge>
        );
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>User Profile</DialogTitle>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-6">
            {/* Profile Header */}
            <div className="flex flex-col items-center text-center space-y-3">
              <Avatar className="h-20 w-20">
                <AvatarFallback className="text-2xl font-bold bg-primary text-primary-foreground">
                  {getInitials(userData.name)}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="text-xl font-semibold">{userData.name}</h3>
                <div className="mt-2">{getAuthBadge()}</div>
              </div>
            </div>

            <Separator />

            {/* User Information */}
            <div className="space-y-4">
              <h4 className="font-semibold text-sm text-muted-foreground uppercase">
                Account Information
              </h4>

              <div className="space-y-3">
                {userData.authMethod !== "guest" && userData.identifier && (
                  <div className="flex items-start gap-3">
                    {userData.authMethod === "aadhaar" ? (
                      <CreditCard className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    ) : (
                      <Phone className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {userData.authMethod === "aadhaar" ? "Aadhaar Number" : "Phone Number"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {userData.authMethod === "aadhaar"
                          ? `XXXX XXXX ${userData.identifier.slice(-4)}`
                          : `+91 ${userData.identifier.slice(0, 5)}XXXXX`}
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex items-start gap-3">
                  <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Member Since</p>
                    <p className="text-sm text-muted-foreground">{userData.joinedDate}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Clock className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Last Active</p>
                    <p className="text-sm text-muted-foreground">{userData.lastActive}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <MessageSquare className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Total Conversations</p>
                    <p className="text-sm text-muted-foreground">{userData.totalChats} chats</p>
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Chat History */}
            <div className="space-y-4">
              <h4 className="font-semibold text-sm text-muted-foreground uppercase">
                Recent Chat History
              </h4>

              {chatHistory.length > 0 ? (
                <ScrollArea className="max-h-72 pr-2">
                  <div className="space-y-2">
                    {chatHistory.map((chat) => (
                      <div
                        key={chat.id}
                        className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{chat.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {chat.messageCount} messages • {chat.date}
                            </p>
                          </div>
                          <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>

              ) : (
                <div className="text-center py-6">
                  <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">No chat history yet</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Start a conversation to see it here
                  </p>
                </div>
              )}
            </div>

            {userData.authMethod === "guest" && (
              <>
                <Separator />
                <div className="p-4 rounded-lg bg-muted/50 border border-dashed">
                  <div className="flex gap-3">
                    <Shield className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">Unlock Full Features</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Login with Aadhaar or Phone to access personalized scheme recommendations,
                        save chat history, and get priority support.
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

export default UserProfileDialog;
