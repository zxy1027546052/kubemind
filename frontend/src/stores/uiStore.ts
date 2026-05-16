import { create } from 'zustand';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timeout?: number;
}

interface UiState {
  sidebarCollapsed: boolean;
  notifications: Notification[];
}

interface UiActions {
  toggleSidebar: () => void;
  addNotification: (n: Omit<Notification, 'id'>) => void;
  dismissNotification: (id: string) => void;
}

export const useUiStore = create<UiState & UiActions>((set) => ({
  sidebarCollapsed: false,
  notifications: [],

  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  addNotification: (n) => {
    const id = `notif-${Date.now().toString(36)}`;
    set((s) => ({ notifications: [...s.notifications, { ...n, id }] }));
    if (n.timeout !== 0) {
      setTimeout(() => {
        set((s) => ({ notifications: s.notifications.filter((x) => x.id !== id) }));
      }, n.timeout ?? 4000);
    }
  },

  dismissNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),
}));
