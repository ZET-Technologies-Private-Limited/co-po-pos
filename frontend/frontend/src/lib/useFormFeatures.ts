/**
 * Custom Hooks for Form Features
 * SF-06: Character counter
 * SF-08: Duplicate check with real-time feedback
 * SF-09: Confirmation before delete
 * SF-10: Tab key navigation
 */

'use client';

import { useState, useCallback, useRef, type KeyboardEvent as ReactKeyboardEvent } from 'react';

// SF-06: Character counter hook
export const useCharacterCounter = (maxLength: number) => {
  const [count, setCount] = useState(0);
  const [isWarning, setIsWarning] = useState(false);

  const handleChange = useCallback((value: string) => {
    const length = value.length;
    setCount(length);
    setIsWarning(length >= maxLength * 0.9);
  }, [maxLength]);

  return { count, maxLength, isWarning, handleChange };
};

// SF-08: Duplicate check with debounce
export const useDuplicateCheck = (checkFn: (value: string) => Promise<boolean>) => {
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkValue = useCallback((value: string) => {
    setIsChecking(true);
    
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = setTimeout(async () => {
      try {
        const duplicate = await checkFn(value);
        setIsDuplicate(duplicate);
      } catch (error) {
        console.error('Duplicate check failed:', error);
      } finally {
        setIsChecking(false);
      }
    }, 500); // 500ms debounce
  }, [checkFn]);

  return { isDuplicate, isChecking, checkValue };
};

// SF-09: Confirmation dialog hook
export const useDeleteConfirmation = () => {
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);

  const requestDelete = useCallback((action: () => void) => {
    setPendingAction(() => action);
    setShowConfirm(true);
  }, []);

  const confirmDelete = useCallback(() => {
    if (pendingAction) {
      pendingAction();
    }
    setShowConfirm(false);
    setPendingAction(null);
  }, [pendingAction]);

  const cancelDelete = useCallback(() => {
    setShowConfirm(false);
    setPendingAction(null);
  }, []);

  return { showConfirm, requestDelete, confirmDelete, cancelDelete };
};

// SF-10: Tab key navigation for tables
export const useTableTabNavigation = (rows: number, cols: number) => {
  const [focusedCell, setFocusedCell] = useState<[number, number]>([0, 0]);

  const handleKeyDown = useCallback((
    e: ReactKeyboardEvent<HTMLInputElement>,
    row: number,
    col: number
  ) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      if (e.shiftKey) {
        // Shift+Tab: Move left or up
        if (col > 0) {
          setFocusedCell([row, col - 1]);
        } else if (row > 0) {
          setFocusedCell([row - 1, cols - 1]);
        }
      } else {
        // Tab: Move right or down
        if (col < cols - 1) {
          setFocusedCell([row, col + 1]);
        } else if (row < rows - 1) {
          setFocusedCell([row + 1, 0]);
        }
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      // Enter moves to next row, same column
      if (row < rows - 1) {
        setFocusedCell([row + 1, col]);
      }
    }
  }, [rows, cols]);

  return { focusedCell, setFocusedCell, handleKeyDown };
};
