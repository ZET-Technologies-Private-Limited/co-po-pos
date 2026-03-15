/**
 * Status Indicators & Colour Logic Utilities (SF-21 to SF-26)
 * Text-only colour conventions for consistent visual hierarchy
 */

// SF-21: CO level text colours
export const getCOLevelColor = (level: 'L1' | 'L2' | 'L3' | null): string => {
  if (!level) return 'text-white/50';
  switch (level) {
    case 'L3':
      return 'text-attain'; // green
    case 'L2':
      return 'text-amber-500'; // amber
    case 'L1':
      return 'text-alert font-bold'; // red bold
    default:
      return 'text-white/50';
  }
};

export const getCOLevelLabel = (level: 'L1' | 'L2' | 'L3'): string => {
  switch (level) {
    case 'L3':
      return 'Highly Achieved';
    case 'L2':
      return 'Partially Achieved';
    case 'L1':
      return 'Not Achieved';
  }
};

// SF-22: Marks status text colours
export const getMarksStatusColor = (status: 'not_started' | 'in_progress' | 'submitted' | 'approved'): string => {
  switch (status) {
    case 'not_started':
      return 'text-white/40'; // grey
    case 'in_progress':
      return 'text-insight'; // blue
    case 'submitted':
      return 'text-amber-500'; // amber
    case 'approved':
      return 'text-attain'; // green
    default:
      return 'text-white/50';
  }
};

export const getMarksStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    not_started: 'Not Started',
    in_progress: 'In Progress',
    submitted: 'Submitted',
    approved: 'Approved',
  };
  return labels[status] || 'Unknown';
};

// SF-23: Wait time text colours
export const getWaitTimeColor = (hours: number): string => {
  if (hours < 24) return 'text-black'; // < 1 day
  if (hours <= 72) return 'text-amber-500'; // 1-3 days
  return 'text-alert'; // > 3 days
};

export const getWaitTimeLabel = (hours: number): string => {
  if (hours < 1) return `${Math.round(hours * 60)} mins`;
  if (hours < 24) return `${Math.round(hours)} hours`;
  const days = Math.round(hours / 24);
  return `${days} day${days > 1 ? 's' : ''}`;
};

// SF-24: Overdue text
export const isOverdue = (deadline: Date): boolean => {
  return new Date() > deadline;
};

export const getOverdueClass = (deadline: Date): string => {
  return isOverdue(deadline) ? 'text-alert font-bold' : '';
};

export const getOverdueText = (deadline: Date): string => {
  if (!isOverdue(deadline)) return '';
  const now = new Date();
  const diff = now.getTime() - deadline.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  return `Overdue by ${days} day${days > 1 ? 's' : ''}`;
};

// SF-25: Attainment percentage colour
export const getAttainmentColor = (percentage: number | null): string => {
  if (percentage === null || percentage === undefined) return 'text-white/40';
  if (percentage >= 60) return 'text-attain'; // green
  if (percentage >= 40) return 'text-amber-500'; // amber
  return 'text-alert'; // red
};

export const getAttainmentLevel = (percentage: number): 'L3' | 'L2' | 'L1' => {
  if (percentage >= 60) return 'L3';
  if (percentage >= 40) return 'L2';
  return 'L1';
};

// SF-26: System status text colours
export const getSystemStatusColor = (status: 'healthy' | 'degraded' | 'down'): string => {
  switch (status) {
    case 'healthy':
      return 'text-attain'; // green
    case 'degraded':
      return 'text-amber-500'; // amber
    case 'down':
      return 'text-alert'; // red
    default:
      return 'text-white/50';
  }
};

export const getSystemStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    healthy: 'Healthy',
    degraded: 'Degraded',
    down: 'Down',
  };
  return labels[status] || 'Unknown';
};
