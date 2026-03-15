/**
 * Navigation & UX Utilities (SF-27 to SF-34)
 * Deep linking, browser navigation, and focus management
 */

'use client';

import { useEffect, useRef, useCallback, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// SF-27: Deep linking - serialize/deserialize page state
export const encodePageState = (state: Record<string, any>): string => {
  return Buffer.from(JSON.stringify(state)).toString('base64');
};

export const decodePageState = (encoded: string): Record<string, any> => {
  try {
    return JSON.parse(Buffer.from(encoded, 'base64').toString('utf-8'));
  } catch {
    return {};
  }
};

// Alternative: Use URLSearchParams for simpler state
export const encodeStateToParams = (state: Record<string, any>): URLSearchParams => {
  const params = new URLSearchParams();
  Object.entries(state).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      params.set(key, String(value));
    }
  });
  return params;
};

export const decodeStateFromParams = (params: URLSearchParams): Record<string, any> => {
  const state: Record<string, any> = {};
  params.forEach((value, key) => {
    // Try to parse as number or boolean
    if (value === 'true') state[key] = true;
    else if (value === 'false') state[key] = false;
    else if (!isNaN(Number(value))) state[key] = Number(value);
    else state[key] = value;
  });
  return state;
};

// SF-28: Browser back button handling is automatic in Next.js
// Just ensure all page transitions use router.push/back properly

// SF-29: Print-optimized layout
export const printOptimizedStyles = `
  @media print {
    /* Hide navigation */
    header, nav, aside, .sidebar, .drawer { display: none !important; }
    
    /* Hide action buttons and filters */
    .action-buttons, .filter-section, .search-bar { display: none !important; }
    
    /* Adjust fonts for print */
    body { font-size: 11pt; line-height: 1.4; }
    h1 { font-size: 18pt; }
    h2 { font-size: 14pt; }
    
    /* Page breaks */
    .page-break { page-break-before: always; }
    
    /* Keep important content visible */
    table { page-break-inside: avoid; }
    tr { page-break-inside: avoid; }
  }
`;

export const triggerPrint = (): void => {
  if (typeof window !== 'undefined') {
    window.print();
  }
};

// SF-30, SF-31, SF-32: Keyboard and focus management
export const useFocusManagement = (focusTargetSelector?: string) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!focusTargetSelector) {
      // Focus first interactive element (input, button, link)
      const focusableElements = ref.current?.querySelectorAll(
        'input, button, [href], [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements?.length) {
        (focusableElements[0] as HTMLElement).focus();
      }
    } else {
      // Focus specific element
      const element = ref.current?.querySelector(focusTargetSelector) as HTMLElement;
      element?.focus();
    }
  }, [focusTargetSelector]);

  return ref;
};

// SF-31: Keyboard navigation helpers
export const handleKeyDown = (e: ReactKeyboardEvent, callbacks: Record<string, () => void>) => {
  const keyMap: Record<string, string> = {
    Escape: 'escape',
    Enter: 'enter',
    ' ': 'space',
    Tab: 'tab',
  };

  const action = keyMap[e.key];
  if (action && callbacks[action]) {
    e.preventDefault();
    callbacks[action]();
  }
};

// SF-33: Auto-redirect on role/context switch
export const useAutoRedirectOnContextChange = (
  context: { academicYear?: string; userRole?: string },
  currentPath: string
) => {
  const router = useRouter();
  const previousContextRef = useRef(context);

  useEffect(() => {
    const hasChanged =
      previousContextRef.current.academicYear !== context.academicYear ||
      previousContextRef.current.userRole !== context.userRole;

    if (hasChanged) {
      previousContextRef.current = context;
      // Reload to get fresh data for new context
      router.refresh();
    }
  }, [context, router]);
};

// SF-34: Read-only mode for past academic years
export const isReadOnlyMode = (academicYear: string, currentYear: string): boolean => {
  const yearNum = parseInt(academicYear.split('-')[0]);
  const currentNum = parseInt(currentYear.split('-')[0]);
  return yearNum < currentNum;
};

export const getReadOnlyBanner = (academicYear: string): string => {
  return `Viewing AY ${academicYear} (Read-only — Historical data)`;
};

export const makeElementReadOnly = (disabled: boolean): Record<string, any> => ({
  disabled,
  'aria-readonly': disabled,
  style: disabled ? { opacity: 0.6, pointerEvents: 'none' } : {},
});

// Hook to manage read-only UI state
export const useReadOnlyMode = (academicYear: string, currentYear: string) => {
  const isReadOnly = isReadOnlyMode(academicYear, currentYear);
  const banner = isReadOnly ? getReadOnlyBanner(academicYear) : null;

  return {
    isReadOnly,
    banner,
    readOnlyProps: makeElementReadOnly(isReadOnly),
  };
};

// SF-27 Extended: Secure deep link generation
export const generateDeepLink = (
  basePath: string,
  state: Record<string, any>
): string => {
  const params = encodeStateToParams(state);
  const query = params.toString();
  return `${basePath}${query ? '?' + query : ''}`;
};

// Restore state from URL
export const useRestoreState = (defaultState: Record<string, any>) => {
  const searchParams = useSearchParams();
  const [state, setState] = useState(defaultState);

  useEffect(() => {
    const restoredState = decodeStateFromParams(searchParams);
    if (Object.keys(restoredState).length > 0) {
      setState(prev => ({ ...prev, ...restoredState }));
    }
  }, [searchParams]);

  return state;
};
