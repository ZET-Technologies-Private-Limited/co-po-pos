/**
 * Security & Session Utilities (SF-58 to SF-63)
 * Auto-save, session management, and audit logging
 */

'use client';

import { useEffect, useRef, useCallback } from 'react';

// SF-58: Auto-save before logout
export interface DraftSession {
  userId: string;
  pageUrl: string;
  data: Record<string, any>;
  savedAt: Date;
  expiresAt: Date;
}

export const AUTO_SAVE_INTERVAL_MS = 30000; // 30 seconds
export const DRAFT_EXPIRY_DAYS = 7;

export const saveDraft = async (
  userId: string,
  pageUrl: string,
  data: Record<string, any>
): Promise<void> => {
  if (typeof window === 'undefined') return;

  const draft: DraftSession = {
    userId,
    pageUrl,
    data,
    savedAt: new Date(),
    expiresAt: new Date(Date.now() + DRAFT_EXPIRY_DAYS * 24 * 60 * 60 * 1000),
  };

  try {
    // Save to localStorage as backup
    localStorage.setItem(`draft_${userId}_${pageUrl}`, JSON.stringify(draft));

    // Send to server
    await fetch('/api/drafts/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    });
  } catch (error) {
    console.error('Failed to save draft:', error);
  }
};

export const retrieveDraft = async (
  userId: string,
  pageUrl: string
): Promise<DraftSession | null> => {
  try {
    const response = await fetch(`/api/drafts/${userId}/${encodeURIComponent(pageUrl)}`);
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
};

export const useAutoSave = (userId: string, pageUrl: string, data: Record<string, any>) => {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Auto-save every 30 seconds
    intervalRef.current = setInterval(() => {
      saveDraft(userId, pageUrl, data);
    }, AUTO_SAVE_INTERVAL_MS);

    // Save on page unload
    const handleBeforeUnload = () => {
      saveDraft(userId, pageUrl, data);
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [userId, pageUrl, data]);
};

// SF-59: Concurrent session warning
export interface SessionAlert {
  currentDevice: string;
  otherDevice: string;
  loginTime: Date;
  location: string;
}

export const checkConcurrentSessions = async (userId: string): Promise<SessionAlert | null> => {
  try {
    const response = await fetch(`/api/sessions/check/${userId}`);
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
};

export const logoutOtherSession = async (userId: string, sessionId: string): Promise<void> => {
  await fetch(`/api/sessions/logout/${userId}/${sessionId}`, {
    method: 'POST',
  });
};

// SF-60: Failed login counter
export const MAX_LOGIN_ATTEMPTS = 5;
export const LOGIN_LOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes

export interface LoginAttempt {
  email: string;
  attempts: number;
  lastAttempt: Date;
  lockedUntil?: Date;
}

export const checkLoginAttempts = async (email: string): Promise<LoginAttempt | null> => {
  try {
    const response = await fetch(`/api/auth/check-attempts/${encodeURIComponent(email)}`);
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
};

export const recordLoginAttempt = async (email: string): Promise<void> => {
  await fetch('/api/auth/record-attempt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
};

export const formatLoginAttemptMessage = (attempt: LoginAttempt): string => {
  const remaining = MAX_LOGIN_ATTEMPTS - attempt.attempts;
  if (remaining <= 0) {
    const lockedUntil = attempt.lockedUntil
      ? new Date(attempt.lockedUntil).toLocaleTimeString()
      : 'in 15 minutes';
    return `Account locked. Try again ${lockedUntil}`;
  }
  return `${remaining} of ${MAX_LOGIN_ATTEMPTS} attempts remaining`;
};

// SF-61: Sensitive data masking
export const maskSensitiveData = (data: any, fieldsToMask: string[]): any => {
  if (typeof data !== 'object') return data;

  const masked = { ...data };
  fieldsToMask.forEach(field => {
    if (field in masked) {
      const value = String(masked[field]);
      masked[field] = value.length > 4 ? '***' + value.slice(-4) : '***';
    }
  });
  return masked;
};

export const isUserAuthorizedForData = (
  userRole: string,
  requiredRoles: string[],
  dataOwnerRole?: string
): boolean => {
  // Admin can see everything
  if (userRole === 'admin') return true;

  // Check if user has required role
  if (!requiredRoles.includes(userRole)) return false;

  // Additional ownership check if applicable
  if (dataOwnerRole && userRole !== 'admin' && userRole !== dataOwnerRole) {
    return false;
  }

  return true;
};

// SF-62: Audit logging for all save operations
export interface AuditEntry {
  id: string;
  userId: string;
  action: string;
  resource: string;
  resourceId: string;
  changes?: {
    field: string;
    oldValue: any;
    newValue: any;
  }[];
  timestamp: Date;
  ipAddress: string;
  userAgent: string;
}

export const logAuditEntry = async (
  userId: string,
  action: string,
  resource: string,
  resourceId: string,
  changes?: AuditEntry['changes']
): Promise<void> => {
  try {
    await fetch('/api/audit/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId,
        action,
        resource,
        resourceId,
        changes,
        timestamp: new Date(),
        ipAddress: await getClientIP(),
        userAgent: navigator.userAgent,
      }),
    });
  } catch (error) {
    console.error('Failed to log audit entry:', error);
  }
};

// SF-62: Auto-log wrapper for save operations
export const withAuditLog = async (
  userId: string,
  action: string,
  resource: string,
  resourceId: string,
  operation: () => Promise<any>,
  oldData?: Record<string, any>,
  newData?: Record<string, any>
): Promise<any> => {
  try {
    const result = await operation();

    // Calculate changes
    const changes: AuditEntry['changes'] = [];
    if (oldData && newData) {
      Object.keys(newData).forEach(key => {
        if (oldData[key] !== newData[key]) {
          changes.push({
            field: key,
            oldValue: oldData[key],
            newValue: newData[key],
          });
        }
      });
    }

    await logAuditEntry(userId, action, resource, resourceId, changes);
    return result;
  } catch (error) {
    // Still log the attempt even if it failed
    await logAuditEntry(userId, `${action} (FAILED)`, resource, resourceId);
    throw error;
  }
};

// SF-63: HTTPS redirect and security headers
export const enforceHTTPS = (): void => {
  if (typeof window !== 'undefined' && window.location.protocol === 'http:') {
    window.location.href = 'https:' + window.location.href.substring(5);
  }
};

export const getSecurityHeaders = (): Record<string, string> => {
  return {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'",
  };
};

// Utility to get client IP (from request if available)
const getClientIP = async (): Promise<string> => {
  try {
    const response = await fetch('/api/auth/ip');
    const data = await response.json();
    return data.ip || 'unknown';
  } catch {
    return 'unknown';
  }
};

// Rate limiting helper
export const createRateLimiter = (maxAttempts: number, windowMs: number) => {
  const attempts = new Map<string, { count: number; firstAttempt: Date }>();

  return {
    check: (key: string): boolean => {
      const now = new Date();
      const entry = attempts.get(key);

      if (!entry) {
        attempts.set(key, { count: 1, firstAttempt: now });
        return true;
      }

      const timeDiff = now.getTime() - entry.firstAttempt.getTime();
      if (timeDiff > windowMs) {
        // Window expired, reset
        attempts.set(key, { count: 1, firstAttempt: now });
        return true;
      }

      entry.count++;
      return entry.count <= maxAttempts;
    },

    reset: (key: string): void => {
      attempts.delete(key);
    },
  };
};
