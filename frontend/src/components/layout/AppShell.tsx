"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AppProviders } from "@/components/providers/AppProviders";
import { BottomNav } from "@/components/layout/BottomNav";
import { Sidebar } from "@/components/layout/Sidebar";

interface UiState {
  sidebarOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
}

const UiContext = createContext<UiState | null>(null);

export function useUi(): UiState {
  const state = useContext(UiContext);
  if (!state) throw new Error("useUi 必须在 AppShell 内使用");
  return state;
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const ui = useMemo<UiState>(
    () => ({
      sidebarOpen,
      openSidebar: () => setSidebarOpen(true),
      closeSidebar: () => setSidebarOpen(false),
    }),
    [sidebarOpen]
  );

  return (
    <UiContext.Provider value={ui}>
      <AppProviders>
        <div className="agent-shell">
          {sidebarOpen ? (
            <button
              className="sidebar-backdrop"
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="关闭菜单"
            />
          ) : null}
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
          <main className="page-area">{children}</main>
          <BottomNav />
        </div>
      </AppProviders>
    </UiContext.Provider>
  );
}
