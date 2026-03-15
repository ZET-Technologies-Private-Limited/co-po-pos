/**
 * Form Utility Functions for Small Features
 * SF-01: Auto-trim whitespace
 * SF-02: Auto-uppercase IDs
 * SF-03: Number input step lock
 * SF-04: Date range validation
 * SF-05: Paste formatting strip
 * SF-08: Duplicate check
 */

// SF-01: Auto-trim whitespace
export const trimWhitespace = (value: string): string => {
  return value.trim();
};

// SF-02: Auto-uppercase IDs
export const uppercaseID = (value: string): string => {
  return value.toUpperCase();
};

// SF-03: Number input step lock - only integers
export const enforceIntegerOnly = (value: string): string => {
  return value.replace(/[^\d]/g, '');
};

// SF-04: Date range validation
export const isDateInRange = (date: string, startDate: string, endDate: string): boolean => {
  const checkDate = new Date(date);
  const start = new Date(startDate);
  const end = new Date(endDate);
  return checkDate >= start && checkDate <= end;
};

// SF-05: Paste formatting strip - plain text only
export const stripPasteFormatting = (html: string): string => {
  const temp = document.createElement('div');
  temp.innerHTML = html;
  return temp.textContent || temp.innerText || '';
};

// SF-06: Character counter
export const getCharCountColor = (current: number, max: number): string => {
  const percentage = (current / max) * 100;
  if (percentage >= 90) return 'text-alert';
  if (percentage >= 70) return 'text-amber-500';
  return 'text-white/50';
};

export const formatCharCount = (current: number, max: number): string => {
  return `${current} / ${max}`;
};

// SF-08: Duplicate check
export const checkDuplicate = async (
  value: string,
  existingValues: string[]
): Promise<boolean> => {
  return existingValues.some(
    existing => existing.toLowerCase() === value.toLowerCase()
  );
};

// Character counter helper
export const getCharacterCountStatus = (
  current: number,
  max: number
): { remaining: number; isWarning: boolean } => {
  const remaining = max - current;
  const isWarning = current >= max * 0.9;
  return { remaining, isWarning };
};

// Required field validation
export const validateRequired = (value: string | number | null | undefined): boolean => {
  if (typeof value === 'string') return value.trim().length > 0;
  return value !== null && value !== undefined;
};
