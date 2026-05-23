import React, { createContext, useContext, useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { UploadModal } from "../UploadModal";

interface UIContextType {
  openUploadModal: () => void;
  closeUploadModal: () => void;
  isUploadModalOpen: boolean;
  notifyUploadSuccess: () => void;
  lastUploadTime: number;
}

const UIContext = createContext<UIContextType | undefined>(undefined);

export const UIProvider = ({ children }: { children: React.ReactNode }) => {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [lastUploadTime, setLastUploadTime] = useState(0);

  const openUploadModal = () => setIsUploadModalOpen(true);
  const closeUploadModal = () => setIsUploadModalOpen(false);
  const notifyUploadSuccess = () => setLastUploadTime(Date.now());

  return (
    <UIContext.Provider value={{ 
      openUploadModal, 
      closeUploadModal, 
      isUploadModalOpen, 
      notifyUploadSuccess,
      lastUploadTime 
    }}>
      {children}
      <UploadModal isOpen={isUploadModalOpen} onClose={closeUploadModal} />
    </UIContext.Provider>
  );
};

export const useUI = () => {
  const context = useContext(UIContext);
  if (context === undefined) {
    throw new Error("useUI must be used within a UIProvider");
  }
  return context;
};

export const AppShell = ({ children }: { children: React.ReactNode }) => {
  return (
    <UIProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />
          <main className="flex-1 p-8 ml-64 overflow-auto">
            {children}
          </main>
        </div>
      </div>
    </UIProvider>
  );
};
