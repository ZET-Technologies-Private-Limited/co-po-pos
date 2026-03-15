/**
 * Data & Calculation Display Utilities (SF-35 to SF-42)
 * Number formatting, rounding, and calculation display
 */

// SF-35: Number rounding
export const roundAttainmentPercent = (value: number | null, decimals: number = 1): string => {
  if (value === null || value === undefined) return 'N/A';
  const rounded = Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
  return rounded.toFixed(decimals) + '%';
};

export const formatStudentMarks = (value: number | null): string => {
  if (value === null || value === undefined) return 'N/A';
  return Math.round(value).toString();
};

// SF-36: Zero handling - distinguish calculated zero from not-yet-calculated
export const formatAttainmentValue = (
  value: number | null | undefined,
  isCalculated: boolean = true
): string => {
  if (value === null || value === undefined) {
    return isCalculated ? '0.0%' : '—';
  }
  return roundAttainmentPercent(value, 1);
};

// SF-37: N/A vs 0 for unattempted questions
export const formatQuestionMarks = (marks: number | null, isAttempted: boolean): string => {
  if (!isAttempted) return 'N/A';
  if (marks === null || marks === undefined) return '0';
  return marks.toString();
};

// SF-38: Live CO preview label
export const getLivePreviewLabel = (isApproved: boolean): string => {
  return isApproved ? 'Official' : 'Estimated';
};

// SF-39: Calculation timestamp
export const formatCalculationTimestamp = (date: Date): string => {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return `Last calculated: ${date.toLocaleDateString()} at ${date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
};

// SF-40: Formula explanation text
export const getAttainmentFormula = (type: 'CO' | 'PO' | 'PSO'): string => {
  switch (type) {
    case 'CO':
      return `
CO Attainment = (Sum of marks in questions mapped to this CO / Total marks in those questions) × 100

Example: If CO3 is mapped to Q2 (5 marks) and Q4 (3 marks):
- Student scores: Q2=4, Q4=2
- Attainment = ((4+2) / (5+3)) × 100 = 75%
- Level: L3 (≥60%)
      `;
    case 'PO':
      return `
PO Attainment = Average of all CO attainments that map to this PO

Example: If PO1 maps to CO1 (75%), CO2 (60%), CO3 (85%):
- Attainment = (75 + 60 + 85) / 3 = 73.3%
- Level: L3 (≥60%)
      `;
    case 'PSO':
      return `
PSO Attainment = Average of all PO attainments that map to this PSO

Example: If PSO1 maps to PO1 (73.3%), PO2 (65%), PO3 (58%):
- Attainment = (73.3 + 65 + 58) / 3 = 65.4%
- Level: L3 (≥60%)
      `;
  }
};

// SF-41: Threshold reference display
export const getThresholdReference = (): { level: 'L3' | 'L2' | 'L1'; range: string }[] => [
  { level: 'L3', range: '≥ 60%' },
  { level: 'L2', range: '40 - 59%' },
  { level: 'L1', range: '< 40%' },
];

export const formatThresholdLine = (): string => 'L3 ≥ 60% | L2 = 40-59% | L1 < 40%';

// SF-42: Overridden value information
export interface OverrideInfo {
  originalValue: number;
  overriddenBy: string;
  overriddenDate: Date;
  reason?: string;
}

export const formatOverrideTooltip = (override: OverrideInfo): string => {
  const date = override.overriddenDate.toLocaleDateString();
  const time = override.overriddenDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  let tooltip = `Original value: ${roundAttainmentPercent(override.originalValue, 1)}\nOverridden by ${override.overriddenBy} on ${date} at ${time}`;
  if (override.reason) {
    tooltip += `\nReason: ${override.reason}`;
  }
  return tooltip;
};

// Helper: Display calculations with confidence
export const formatWithConfidence = (value: number, confidence: number): string => {
  // confidence is 0-100
  const confidenceLabel =
    confidence >= 90
      ? '(very high confidence)'
      : confidence >= 70
        ? '(high confidence)'
        : confidence >= 50
          ? '(moderate confidence)'
          : '(low confidence)';

  return `${roundAttainmentPercent(value, 1)} ${confidenceLabel}`;
};
