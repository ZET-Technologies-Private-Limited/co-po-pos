'use client';

import React, { useState, useCallback } from 'react';
import {
  trimWhitespace,
  uppercaseID,
  enforceIntegerOnly,
  stripPasteFormatting,
  validateRequired,
  getCharacterCountStatus,
} from '@/lib/formUtils';
import { useCharacterCounter, useDuplicateCheck } from '@/lib/useFormFeatures';

interface FormInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  type?: 'text' | 'email' | 'number' | 'date' | 'password' | 'textarea';
  placeholder?: string;
  required?: boolean;
  autoTrim?: boolean; // SF-01
  autoUppercase?: boolean; // SF-02
  integerOnly?: boolean; // SF-03
  maxLength?: number; // SF-06
  showCharCounter?: boolean; // SF-06
  duplicateCheckFn?: (value: string) => Promise<boolean>; // SF-08
  errorMessage?: string;
  helpText?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Reusable Form Input Component with Small Features
 * Integrates SF-01, SF-02, SF-03, SF-05, SF-06, SF-07, SF-08
 */
export const FormInput: React.FC<FormInputProps> = ({
  label,
  value,
  onChange,
  onBlur,
  type = 'text',
  placeholder,
  required = false,
  autoTrim = false,
  autoUppercase = false,
  integerOnly = false,
  maxLength,
  showCharCounter = false,
  duplicateCheckFn,
  errorMessage,
  helpText,
  disabled = false,
  className = '',
}) => {
  const [internalError, setInternalError] = useState<string>('');
  const charCounter = showCharCounter ? useCharacterCounter(maxLength || 100) : null;
  const duplicateCheck = duplicateCheckFn ? useDuplicateCheck(duplicateCheckFn) : null;

  const handleChange = useCallback(
    (newValue: string) => {
      let processedValue = newValue;

      // SF-03: Enforce integer only
      if (integerOnly) {
        processedValue = enforceIntegerOnly(processedValue);
      }

      // SF-02: Auto-uppercase IDs
      if (autoUppercase) {
        processedValue = uppercaseID(processedValue);
      }

      // SF-06: Character counter
      if (charCounter && type !== 'date') {
        charCounter.handleChange(processedValue);
      }

      onChange(processedValue);
    },
    [onChange, integerOnly, autoUppercase, charCounter, type]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
      if (type === 'textarea') {
        e.preventDefault();
        const pastedText = e.clipboardData.getData('text/plain');
        const cleanText = stripPasteFormatting(pastedText);
        handleChange(cleanText);
      }
    },
    [type, handleChange]
  );

  const handleBlur = useCallback(() => {
    // SF-01: Auto-trim on blur
    if (autoTrim && value) {
      const trimmedValue = trimWhitespace(value);
      onChange(trimmedValue);
    }

    // SF-08: Duplicate check on blur
    if (duplicateCheckFn && value) {
      duplicateCheck?.checkValue(value);
    }

    onBlur?.();
  }, [value, autoTrim, onChange, duplicateCheckFn, duplicateCheck, onBlur]);

  const displayError = errorMessage || internalError;
  const isInvalid = !!displayError || duplicateCheck?.isDuplicate;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-sm font-medium text-white/80">
        {label}
        {/* SF-07: Required field asterisk */}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {type === 'textarea' ? (
        <textarea
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onBlur={handleBlur}
          onPaste={handlePaste}
          placeholder={placeholder}
          maxLength={maxLength}
          disabled={disabled}
          className={`px-3 py-2 bg-white/5 border rounded-lg text-white placeholder-white/30 outline-none focus:border-brand transition-colors ${
            isInvalid ? 'border-red-500' : 'border-white/10'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onBlur={handleBlur}
          onPaste={handlePaste}
          placeholder={placeholder}
          maxLength={maxLength}
          disabled={disabled}
          className={`px-3 py-2 bg-white/5 border rounded-lg text-white placeholder-white/30 outline-none focus:border-brand transition-colors ${
            isInvalid ? 'border-red-500' : 'border-white/10'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
      )}

      {/* SF-06: Character counter */}
      {showCharCounter && charCounter && (
        <div
          className={`text-xs font-mono ${
            charCounter.isWarning ? 'text-red-400' : 'text-white/50'
          }`}
        >
          {charCounter.count} / {charCounter.maxLength} characters
        </div>
      )}

      {/* SF-08: Duplicate check feedback */}
      {duplicateCheck && (
        <>
          {duplicateCheck.isChecking && (
            <div className="text-xs text-blue-400">Checking...</div>
          )}
          {duplicateCheck.isDuplicate && (
            <div className="text-xs text-red-400">This value already exists</div>
          )}
        </>
      )}

      {/* Error message */}
      {displayError && (
        <div className="text-xs text-red-400">{displayError}</div>
      )}

      {/* Help text */}
      {helpText && !displayError && (
        <div className="text-xs text-white/50">{helpText}</div>
      )}
    </div>
  );
};

export default FormInput;
