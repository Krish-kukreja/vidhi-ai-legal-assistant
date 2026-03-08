// User data management utilities

export interface UserData {
  name: string;
  authMethod: "guest" | "aadhaar" | "phone";
  identifier?: string;
  joinedDate: string;
  totalChats: number;
  lastActive: string;
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  date: string;
  messageCount: number;
  description?: string;
  folderId?: string;
  messages?: any[];
}

export interface ChatFolder {
  id: string;
  name: string;
}

// Get user data from localStorage
export const getUserData = (): UserData | null => {
  const authToken = localStorage.getItem("vidhi_auth");
  const storedUserData = localStorage.getItem("vidhi_user_data");

  if (!authToken) {
    return null;
  }

  // If we have stored user data, return it
  if (storedUserData) {
    return JSON.parse(storedUserData);
  }

  // Parse auth token to create user data
  if (authToken.startsWith("aadhaar_")) {
    const aadhaarNumber = authToken.replace("aadhaar_", "");
    const userData: UserData = {
      name: "Aadhaar User",
      authMethod: "aadhaar",
      identifier: aadhaarNumber,
      joinedDate: new Date().toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
      totalChats: 0,
      lastActive: "Just now",
    };
    saveUserData(userData);
    return userData;
  }

  if (authToken.startsWith("phone_")) {
    const phoneNumber = authToken.replace("phone_", "");
    const userData: UserData = {
      name: "Phone User",
      authMethod: "phone",
      identifier: phoneNumber,
      joinedDate: new Date().toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
      totalChats: 0,
      lastActive: "Just now",
    };
    saveUserData(userData);
    return userData;
  }

  // Guest user
  const userData: UserData = {
    name: "Guest User",
    authMethod: "guest",
    joinedDate: new Date().toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    }),
    totalChats: 0,
    lastActive: "Just now",
  };
  saveUserData(userData);
  return userData;
};

// Save user data to localStorage
export const saveUserData = (userData: UserData) => {
  localStorage.setItem("vidhi_user_data", JSON.stringify(userData));
};

// Update user name
export const updateUserName = (name: string) => {
  const userData = getUserData();
  if (userData) {
    userData.name = name;
    saveUserData(userData);
  }
};

// Update last active timestamp
export const updateLastActive = () => {
  const userData = getUserData();
  if (userData) {
    userData.lastActive = "Just now";
    saveUserData(userData);
  }
};


// Increment chat count
export const incrementChatCount = () => {
  const userData = getUserData();
  if (userData) {
    userData.totalChats += 1;
    saveUserData(userData);
  }
};

// --- FOLDERS API ---
export const getFolders = (): ChatFolder[] => {
  const folders = localStorage.getItem("vidhi_chat_folders");
  if (!folders) return [];
  return JSON.parse(folders);
};

export const createFolder = (name: string): ChatFolder => {
  const folders = getFolders();
  const newFolder: ChatFolder = {
    id: `folder_${Date.now()}`,
    name,
  };
  folders.push(newFolder);
  localStorage.setItem("vidhi_chat_folders", JSON.stringify(folders));
  return newFolder;
};

export const deleteFolder = (id: string) => {
  const folders = getFolders();
  const updatedFolders = folders.filter((f) => f.id !== id);
  localStorage.setItem("vidhi_chat_folders", JSON.stringify(updatedFolders));

  // Remove folderId from any chats in this folder
  const history = getChatHistory();
  const updatedHistory = history.map(chat =>
    chat.folderId === id ? { ...chat, folderId: undefined } : chat
  );
  localStorage.setItem("vidhi_chat_history", JSON.stringify(updatedHistory));
};

// --- CHAT HISTORY API ---
export const getChatHistory = (): ChatHistoryItem[] => {
  const history = localStorage.getItem("vidhi_chat_history");
  if (!history) {
    return [];
  }
  return JSON.parse(history);
};

export const saveChatToHistory = (title: string, messages: any[]) => {
  const history = getChatHistory();
  const newChat: ChatHistoryItem = {
    id: `chat_${Date.now()}`,
    title: title.slice(0, 50) + (title.length > 50 ? "..." : ""),
    date: new Date().toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }),
    messageCount: messages.length,
    messages: messages,
  };

  // Add to beginning of array
  history.unshift(newChat);
  // Optional: you can un-cap to say keep 100 instead of 10 if you want folders
  const trimmedHistory = history.slice(0, 100);

  localStorage.setItem("vidhi_chat_history", JSON.stringify(trimmedHistory));
  incrementChatCount();
  return newChat;
};

export const updateChatDetails = (id: string, updates: Partial<ChatHistoryItem>) => {
  const history = getChatHistory();
  const updatedHistory = history.map(chat =>
    chat.id === id ? { ...chat, ...updates } : chat
  );
  localStorage.setItem("vidhi_chat_history", JSON.stringify(updatedHistory));
};

// Clear user data (logout)
export const clearUserData = () => {
  localStorage.removeItem("vidhi_auth");
  localStorage.removeItem("vidhi_user_data");
  localStorage.removeItem("vidhi_chat_history");
};

// Get display name for user
export const getDisplayName = (): string => {
  const userData = getUserData();
  if (!userData) {
    return "VIDHI User";
  }
  return userData.name;
};

// Get user initials for avatar
export const getUserInitials = (): string => {
  const name = getDisplayName();
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
};
