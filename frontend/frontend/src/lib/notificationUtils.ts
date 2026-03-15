/**
 * Notification & Alert Utilities (SF-51 to SF-57)
 * Toast messages, banners, and email notifications
 */

'use client';

import { useState, useCallback, useRef } from 'react';

// SF-51: In-page alert banners (high-priority warnings)
export interface AlertBanner {
  id: string;
  type: 'error' | 'warning' | 'info' | 'success';
  title: string;
  message: string;
  action?: { label: string; handler: () => void };
  closeable?: boolean;
}

// SF-52: Toast notifications (auto-dismiss)
export interface ToastNotification {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
  duration?: number; // ms, default 4000
  action?: { label: string; handler: () => void };
}

// SF-55: Deadline countdown
export interface DeadlineAlert {
  examName: string;
  term: string;
  hoursRemaining: number;
  isUrgent: boolean; // true if < 3 days (72 hours)
}

// Hook for managing toast notifications
export const useToastManager = () => {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const timeoutRefs = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const addToast = useCallback((notification: Omit<ToastNotification, 'id'>) => {
    const id = Date.now().toString();
    const duration = notification.duration || 4000;

    // Errors don't auto-dismiss
    const shouldAutoDismiss = notification.type !== 'error';

    setToasts(prev => [
      ...prev,
      { ...notification, id, duration: shouldAutoDismiss ? duration : undefined },
    ]);

    if (shouldAutoDismiss) {
      const timeout = setTimeout(() => removeToast(id), duration);
      timeoutRefs.current.set(id, timeout);
    }
  }, []);

  const removeToast = useCallback((id: string) => {
    // Clear timeout if exists
    const timeout = timeoutRefs.current.get(id);
    if (timeout) {
      clearTimeout(timeout);
      timeoutRefs.current.delete(id);
    }

    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addSuccess = useCallback(
    (message: string) => addToast({ type: 'success', message }),
    [addToast]
  );

  const addError = useCallback(
    (message: string) => addToast({ type: 'error', message }),
    [addToast]
  );

  const addWarning = useCallback(
    (message: string) => addToast({ type: 'warning', message }),
    [addToast]
  );

  const addInfo = useCallback(
    (message: string) => addToast({ type: 'info', message }),
    [addToast]
  );

  return {
    toasts,
    addToast,
    addSuccess,
    addError,
    addWarning,
    addInfo,
    removeToast,
  };
};

// SF-54: Batch notification deduplication
export interface BatchedNotification {
  userId: string;
  type: string;
  count: number;
  firstOccurrence: Date;
  lastOccurrence: Date;
  items: string[]; // identifiers of related items
}

export const deduplicateNotifications = (
  notifications: any[],
  groupByFields: string[] = ['userId', 'type']
): BatchedNotification[] => {
  const grouped = notifications.reduce(
    (acc, notif) => {
      const key = groupByFields.map(f => notif[f]).join('|');
      if (!acc[key]) {
        acc[key] = {
          ...notif,
          count: 1,
          items: [notif.itemId || notif.id],
        };
      } else {
        acc[key].count++;
        acc[key].lastOccurrence = new Date();
        acc[key].items.push(notif.itemId || notif.id);
      }
      return acc;
    },
    {} as Record<string, BatchedNotification>
  );

  return Object.values(grouped);
};

// SF-55: Deadline countdown
export const calculateDeadlineCountdown = (deadline: Date): DeadlineAlert | null => {
  const now = new Date();
  if (now > deadline) return null; // Already passed

  const diffMs = deadline.getTime() - now.getTime();
  const hoursRemaining = Math.ceil(diffMs / (1000 * 60 * 60));

  return {
    examName: '', // Set by caller
    term: '', // Set by caller
    hoursRemaining,
    isUrgent: hoursRemaining < 72, // < 3 days
  };
};

export const formatDeadlineCountdown = (alert: DeadlineAlert): string => {
  if (alert.hoursRemaining <= 24) {
    return `${alert.term} marks due in ${Math.round(alert.hoursRemaining / 24)} day${
      Math.round(alert.hoursRemaining / 24) > 1 ? 's' : ''
    }`;
  }
  return `${alert.term} marks due in ${Math.ceil(alert.hoursRemaining / 24)} days`;
};

// SF-56: Email notification format (plain text)
export interface EmailNotification {
  to: string;
  subject: string;
  bodyPlain: string; // Plain text, no HTML
  actionLink?: {
    label: string;
    url: string;
  };
}

export const formatEmailNotification = (
  subject: string,
  body: string,
  action?: { label: string; url: string }
): EmailNotification => {
  let bodyPlain = `${subject}\n\n${body}`;

  if (action) {
    bodyPlain += `\n\n${action.label}: ${action.url}`;
  }

  bodyPlain += '\n\n---\nDo not reply to this email.';

  return {
    to: '', // Set by caller
    subject: `[Co-PO] ${subject}`,
    bodyPlain,
    actionLink: action,
  };
};

// SF-57: Do Not Disturb settings
export interface DNDSettings {
  enabled: boolean;
  startHour: number; // 0-23
  endHour: number; // 0-23
}

export const isInDNDWindow = (dndSettings: DNDSettings): boolean => {
  if (!dndSettings.enabled) return false;

  const now = new Date();
  const currentHour = now.getHours();

  if (dndSettings.startHour < dndSettings.endHour) {
    return currentHour >= dndSettings.startHour && currentHour < dndSettings.endHour;
  } else {
    // Range wraps around midnight
    return currentHour >= dndSettings.startHour || currentHour < dndSettings.endHour;
  }
};

export const shouldSendNotificationNow = (
  notificationType: 'in-app' | 'email',
  dndSettings: DNDSettings
): boolean => {
  // In-app notifications are always sent
  if (notificationType === 'in-app') return true;

  // Email notifications are held during DND, sent after
  return !isInDNDWindow(dndSettings);
};

export const getNextDNDEndTime = (dndSettings: DNDSettings): Date | null => {
  if (!dndSettings.enabled) return null;

  const now = new Date();
  const nextEnd = new Date(now);
  nextEnd.setHours(dndSettings.endHour, 0, 0, 0);

  if (nextEnd <= now) {
    // Already passed today, set for tomorrow
    nextEnd.setDate(nextEnd.getDate() + 1);
  }

  return nextEnd;
};

// Hook for SNooze banner alerts
export const useAlertBanners = () => {
  const [banners, setBanners] = useState<AlertBanner[]>([]);

  const addBanner = useCallback((banner: Omit<AlertBanner, 'id'>) => {
    const id = Date.now().toString();
    setBanners(prev => [...prev, { ...banner, id }]);
  }, []);

  const removeBanner = useCallback((id: string) => {
    setBanners(prev => prev.filter(b => b.id !== id));
  }, []);

  return {
    banners,
    addBanner,
    removeBanner,
  };
};
