import { useState, useEffect } from "react";
import { MessageSquare, Plus, ChevronRight, Folder, MoreVertical, Edit2, Trash2, FolderPlus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import UserProfileDialog from "./UserProfileDialog";
import {
  getUserData, getChatHistory, getDisplayName, getUserInitials,
  getFolders, createFolder, deleteFolder, updateChatDetails
} from "@/utils/userStorage";
import type { UserData, ChatHistoryItem, ChatFolder } from "@/utils/userStorage";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat?: () => void;
  onSelectChat?: (chatId: string) => void;
  activeChatId?: string | null;
}

const ChatSidebar = ({ isOpen, onClose, onNewChat, onSelectChat, activeChatId }: ChatSidebarProps) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const [userData, setUserData] = useState<UserData | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [folders, setFolders] = useState<ChatFolder[]>([]);
  const [displayName, setDisplayName] = useState("VIDHI User");
  const [userInitials, setUserInitials] = useState("V");

  // Dialog states
  const [isFolderDialogOpen, setIsFolderDialogOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingChat, setEditingChat] = useState<ChatHistoryItem | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const loadData = () => {
    setUserData(getUserData());
    setDisplayName(getDisplayName());
    setUserInitials(getUserInitials());
    setChatHistory(getChatHistory());
    setFolders(getFolders());
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const handleCreateFolder = () => {
    if (newFolderName.trim()) {
      createFolder(newFolderName.trim());
      setNewFolderName("");
      setIsFolderDialogOpen(false);
      loadData();
    }
  };

  const handleSaveEdit = () => {
    if (editingChat && editTitle.trim()) {
      updateChatDetails(editingChat.id, {
        title: editTitle.trim(),
        description: editDescription.trim()
      });
      setIsEditDialogOpen(false);
      loadData();
    }
  };

  const moveToFolder = (chatId: string, folderId: string | undefined) => {
    updateChatDetails(chatId, { folderId });
    loadData();
  };

  const getSubtitle = () => {
    if (!userData) return "Free Legal Aid";
    switch (userData.authMethod) {
      case "aadhaar": return "Aadhaar Verified";
      case "phone": return "Phone Verified";
      case "guest": return "Guest Mode";
      default: return "Free Legal Aid";
    }
  };

  const unassignedChats = chatHistory.filter((c) => !c.folderId);

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-30 bg-foreground/30 lg:hidden" onClick={onClose} />
      )}
      <motion.aside
        className={`fixed lg:static z-40 top-0 left-0 h-full w-72 bg-sidebar flex flex-col border-r border-sidebar-border transition-transform lg:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
        initial={false}
      >
        <div className="p-4 border-b border-sidebar-border flex gap-2">
          <button
            onClick={onNewChat}
            className="flex-1 flex items-center justify-center gap-2 bg-sidebar-primary text-sidebar-primary-foreground rounded-xl py-3 font-semibold hover:opacity-90 transition-opacity"
          >
            <Plus className="h-5 w-5" />
            New Chat
          </button>
          <button
            onClick={() => setIsFolderDialogOpen(true)}
            className="w-12 flex items-center justify-center bg-sidebar-accent text-sidebar-foreground rounded-xl hover:bg-sidebar-accent/80 transition-colors"
            title="New Folder"
          >
            <FolderPlus className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-4">

          {/* FOLDERS */}
          {folders.map((folder) => {
            const folderChats = chatHistory.filter((c) => c.folderId === folder.id);
            return (
              <div key={folder.id} className="flex flex-col gap-1">
                <div className="flex items-center justify-between px-2 py-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-sidebar-foreground">
                    <Folder className="h-3.5 w-3.5" />
                    {folder.name}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button className="p-1 rounded hover:bg-sidebar-accent">
                        <MoreVertical className="h-3.5 w-3.5 text-sidebar-muted" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem className="text-destructive" onClick={() => { deleteFolder(folder.id); loadData(); }}>
                        <Trash2 className="h-4 w-4 mr-2" /> Delete Folder
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                {folderChats.length === 0 ? (
                  <div className="px-4 py-2 text-xs text-sidebar-muted italic">Empty</div>
                ) : (
                  folderChats.map((chat) => (
                    <ChatItem
                      key={chat.id}
                      chat={chat}
                      folders={folders}
                      isActive={activeChatId === chat.id}
                      onSelect={() => onSelectChat && onSelectChat(chat.id)}
                      onEdit={() => { setEditingChat(chat); setEditTitle(chat.title); setEditDescription(chat.description || ""); setIsEditDialogOpen(true); }}
                      onMove={(fId) => moveToFolder(chat.id, fId)}
                    />
                  ))
                )}
              </div>
            );
          })}

          {/* RECENT UNASSIGNED */}
          <div className="flex flex-col gap-1">
            <div className="px-2 py-1.5 text-xs font-semibold text-sidebar-muted">Recent</div>
            {unassignedChats.length === 0 && folders.length === 0 ? (
              <div className="flex flex-col items-center justify-center mt-6">
                <MessageSquare className="h-8 w-8 text-sidebar-muted mb-3" />
                <p className="text-sm text-sidebar-muted text-center">No chat history</p>
              </div>
            ) : (
              unassignedChats.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  folders={folders}
                  isActive={activeChatId === chat.id}
                  onSelect={() => onSelectChat && onSelectChat(chat.id)}
                  onEdit={() => { setEditingChat(chat); setEditTitle(chat.title); setEditDescription(chat.description || ""); setIsEditDialogOpen(true); }}
                  onMove={(fId) => moveToFolder(chat.id, fId)}
                />
              ))
            )}
          </div>

        </div>

        <div className="p-4 border-t border-sidebar-border">
          <button
            onClick={() => setProfileOpen(true)}
            className="w-full flex items-center gap-3 hover:bg-sidebar-accent rounded-lg p-2 -m-2 transition-colors group"
          >
            <div className="w-9 h-9 rounded-full bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-sm flex-shrink-0">
              {userInitials}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium text-sidebar-foreground truncate">{displayName}</p>
              <p className="text-xs text-sidebar-muted truncate">{getSubtitle()}</p>
            </div>
            <ChevronRight className="h-4 w-4 text-sidebar-muted group-hover:text-sidebar-foreground transition-colors flex-shrink-0" />
          </button>
        </div>
      </motion.aside>

      {/* NEW FOLDER DIALOG */}
      <Dialog open={isFolderDialogOpen} onOpenChange={setIsFolderDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Folder</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Folder Name</Label>
              <Input value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} placeholder="e.g. Property Disputes" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsFolderDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateFolder}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EDIT CHAT DIALOG */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chat Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Title</Label>
              <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Enter a custom title" />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder="Add a short note about this chat" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveEdit}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {userData && (
        <UserProfileDialog
          isOpen={profileOpen}
          onClose={() => setProfileOpen(false)}
          userData={userData}
          chatHistory={chatHistory}
        />
      )}
    </>
  );
};

// Extracted ChatItem Component
const ChatItem = ({
  chat,
  folders,
  isActive,
  onSelect,
  onEdit,
  onMove
}: {
  chat: ChatHistoryItem,
  folders: ChatFolder[],
  isActive: boolean,
  onSelect: () => void,
  onEdit: () => void,
  onMove: (id?: string) => void
}) => {
  return (
    <div className={`w-full flex items-center gap-2 group relative rounded-lg transition-colors ${isActive ? 'bg-sidebar-accent' : 'hover:bg-sidebar-accent'}`}>
      <button
        onClick={onSelect}
        className="flex-1 flex items-center gap-3 px-3 py-2.5 text-left text-sidebar-foreground"
      >
        <MessageSquare className={`h-4 w-4 transition-colors flex-shrink-0 ${isActive ? 'text-sidebar-foreground' : 'text-sidebar-muted group-hover:text-sidebar-foreground'}`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate font-medium">{chat.title}</p>
          {chat.description && <p className="text-[10px] text-sidebar-muted truncate">{chat.description}</p>}
        </div>
      </button>

      <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute right-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="p-1.5 rounded-md hover:bg-background shadow-sm bg-sidebar-accent text-sidebar-foreground">
              <MoreVertical className="h-3.5 w-3.5" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={onEdit}>
              <Edit2 className="mr-2 h-4 w-4" /> Edit Details
            </DropdownMenuItem>

            {folders.length > 0 && <DropdownMenuSeparator />}

            {folders.map(f => (
              <DropdownMenuItem key={f.id} onClick={() => onMove(f.id)}>
                <Folder className="mr-2 h-4 w-4" /> Move to {f.name}
              </DropdownMenuItem>
            ))}
            {chat.folderId && (
              <DropdownMenuItem onClick={() => onMove(undefined)}>
                <Folder className="mr-2 h-4 w-4" /> Remove from Folder
              </DropdownMenuItem>
            )}

          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
};

export default ChatSidebar;
