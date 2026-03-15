import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Toast = {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
};

export type NotifType = 'co_alert' | 'marks' | 'approval' | 'deadline' | 'system';

export type Notification = {
  id: string;
  title: string;
  desc: string;
  time: string;
  read: boolean;
  type: NotifType;
  actionLabel?: string;
  actionHref?: string;
};

export type Language = 'en' | 'hi' | 'ta' | 'te';

interface UIState {
  // Toast
  toasts: Toast[];
  addToast: (message: string, type?: Toast['type']) => void;
  removeToast: (id: string) => void;

  // Notifications panel
  notifOpen: boolean;
  notifications: Notification[];
  openNotif: () => void;
  closeNotif: () => void;
  markAllRead: () => void;
  markRead: (id: string) => void;

  // Global search
  searchOpen: boolean;
  openSearch: () => void;
  closeSearch: () => void;

  // Profile menu
  profileMenuOpen: boolean;
  openProfileMenu: () => void;
  closeProfileMenu: () => void;

  // Dark mode (persisted)
  darkMode: boolean;
  toggleDarkMode: () => void;

  // Language (persisted)
  language: Language;
  setLanguage: (lang: Language) => void;

  // Session timeout
  sessionWarning: boolean;
  setSessionWarning: (v: boolean) => void;

  // Global OBE Chatbot (floating orb)
  chatOpen: boolean;
  openChat: () => void;
  closeChat: () => void;
}

const SEED_NOTIFICATIONS: Notification[] = [
  { id: 'n1', title: 'CO Attainment Computed', desc: 'DBMS-301 · CO attainment report is ready to view', time: '5 min ago', read: false, type: 'co_alert', actionLabel: 'View CO Attainment', actionHref: '/courses/cs301/co-attainment' },
  { id: 'n2', title: 'AI Analysis Complete', desc: 'ML-401 · Question Bloom classification finished', time: '45 min ago', read: false, type: 'marks', actionLabel: 'Go to Marks Page', actionHref: '/courses/cs401' },
  { id: 'n3', title: 'At-Risk Alert', desc: 'EC201 attainment dropped below 60% threshold', time: '2 hrs ago', read: false, type: 'co_alert', actionLabel: 'View CO Attainment', actionHref: '/low-co-alerts' },
  { id: 'n4', title: 'Marks Approval Pending', desc: 'CS301 T2 marks submitted — awaiting subject lead approval', time: '3 hrs ago', read: false, type: 'approval', actionLabel: 'Review Approval', actionHref: '/lead/marks-approval' },
  { id: 'n5', title: 'Submission Deadline', desc: 'SEE marks entry closes in 48 hours for CS501', time: '4 hrs ago', read: false, type: 'deadline', actionLabel: 'Go to Marks Page', actionHref: '/courses/cs501' },
  { id: 'n6', title: 'Report Generated', desc: 'PO Attainment Report for AY 2025-26 exported as PDF', time: '5 hrs ago', read: true, type: 'system', actionLabel: 'View Report', actionHref: '/reports' },
  { id: 'n7', title: 'Marks Uploaded', desc: 'CS301 T2 marks imported from Excel successfully', time: 'Yesterday', read: true, type: 'marks', actionLabel: 'Go to Marks Page', actionHref: '/courses/cs301' },
];

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      toasts: [],
      addToast: (message, type = 'info') => {
        const id = Date.now().toString();
        set(s => ({ toasts: [...s.toasts, { id, message, type }] }));
        if (type !== 'error') {
          const timeout = type === 'warning' ? 7000 : 4500;
          setTimeout(() => get().removeToast(id), timeout);
        }
      },
      removeToast: (id) => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),

      notifOpen: false,
      notifications: SEED_NOTIFICATIONS,
      openNotif: () => set({ notifOpen: true }),
      closeNotif: () => set({ notifOpen: false }),
      markAllRead: () => set(s => ({ notifications: s.notifications.map(n => ({ ...n, read: true })) })),
      markRead: (id) => set(s => ({ notifications: s.notifications.map(n => n.id === id ? { ...n, read: true } : n) })),

      searchOpen: false,
      openSearch: () => set({ searchOpen: true }),
      closeSearch: () => set({ searchOpen: false }),

      profileMenuOpen: false,
      openProfileMenu: () => set({ profileMenuOpen: true }),
      closeProfileMenu: () => set({ profileMenuOpen: false }),

      darkMode: true,
      toggleDarkMode: () => set(s => ({ darkMode: !s.darkMode })),

      language: 'en',
      setLanguage: (lang) => set({ language: lang }),

      sessionWarning: false,
      setSessionWarning: (v) => set({ sessionWarning: v }),

      chatOpen: false,
      openChat: () => set({ chatOpen: true }),
      closeChat: () => set({ chatOpen: false }),
    }),
    {
      name: 'obe-ui-prefs',
      partialize: (s) => ({ darkMode: s.darkMode, language: s.language, notifications: s.notifications }),
    }
  )
);
