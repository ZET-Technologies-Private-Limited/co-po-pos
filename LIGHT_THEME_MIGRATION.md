# Light Theme Migration Guide

## Overview
This document outlines the comprehensive light theme redesign for the CO-PO-PSO Mapping System. The application is being transformed from a dark cosmic theme to a professional light theme suitable for a university platform.

## Color Palette - Light Theme

### Primary Colors
- **Background**: #FFFFFF (Pure White)
- **Surface**: #F9FAFB (Off-white for cards/containers)
- **Surface Secondary**: #F3F4F6 (Light gray for hover states)

### Text Colors
- **Primary Text**: #1F2937 (Dark gray - default text)
- **Secondary Text**: #6B7280 (Medium gray - supporting text)
- **Tertiary Text**: #9CA3AF (Light gray - captions)

### Brand & Semantic Colors
- **Brand**: #2563EB (Professional Blue)
- **Brand Hover**: #1D4ED8 (Darker Blue)
- **Brand Light**: #DBEAFE (Light Blue background)
- **Success**: #10B981 (Green)
- **Warning**: #F59E0B (Amber/Orange)
- **Error**: #EF4444 (Red)
- **Aurora**: #06B6D4 (Cyan)
- **Accent**: #7C3AED (Purple)

### Border Colors
- **Border**: #E5E7EB (Gray-300)
- **Border Light**: #F0F1F3 (Very light border)

## Changes Made So Far

### 1. Core Theme System ✅
- **File**: `/app/globals.css`
- Updated CSS variables for light theme
- Added utility classes (.bg-primary, .bg-secondary, .text-muted, etc.)
- Updated typography to use gray-900 for headings

### 2. Root Layout ✅
- **File**: `/app/layout.tsx`
- Changed background from `bg-cosmic` to `bg-white`
- Updated text color from `text-surface` to `text-gray-900`

### 3. App Layout (Header & Navigation) ✅
- **File**: `/app/(app)/layout.tsx`
- Updated header background to white with gray border
- Changed all navigation button colors to gray with blue active states
- Updated mobile menu styling
- Changed notification badge to red
- Updated profile avatar styling

### 4. Authentication Background ✅
- **File**: `/components/auth/LoginBackground.tsx`
- Updated gradient overlays to light theme
- Reduced opacity for better readability

### 5. Login Page (Partial) ✅
- **File**: `/app/(auth)/login/page.tsx`
- Updated role selector colors
- Updated role meta colors
- Updated session warning modal styling

### 6. UI Components ✅
- **ToastContainer**: Updated to white background with light borders
- **NotificationsPanel**: Updated to light theme styling
- Type colors updated (success/error/warning/info)

## Remaining Work

### Priority 1 - Critical UI Components
These files appear in many pages and have high impact:

1. **ProfileMenu** (`/components/ui/ProfileMenu.tsx`)
   - Background: white
   - Borders: gray-200
   - Text: gray-900 / gray-600
   - Hover: gray-100
   - Icons: gray-600

2. **GlobalSearch** (`/components/ui/GlobalSearch.tsx`)
   - Modal background: white
   - Search input: bg-gray-50
   - Results: white with gray-200 border

3. **SessionTimeoutModal** (`/components/ui/SessionTimeoutModal.tsx`)
   - Background: white
   - Borders: gray-200
   - Button: blue-600

4. **FormInput** (`/components/ui/FormInput.tsx`)
   - Input background: white
   - Border: gray-300
   - Text: gray-900
   - Focus ring: blue-500

5. **DataTable** (`/components/ui/DataTable.tsx`)
   - Background: white
   - Rows: alternate white/gray-50
   - Headers: gray-100
   - Borders: gray-200

6. **MarksEntryTable** (`/components/ui/MarksEntryTable.tsx`)
   - Similar to DataTable

### Priority 2 - Dashboard Components
These are seen by all roles:

1. **Dashboard Pages**:
   - `/app/(app)/dashboard/page.tsx`
   - `/app/(app)/admin/dashboard/page.tsx`
   - `/app/(app)/faculty/dashboard/page.tsx`
   - `/app/(app)/student/dashboard/page.tsx`
   - `/app/(app)/hod/dashboard/page.tsx`
   - `/app/(app)/lead/dashboard/page.tsx`

2. **Dashboard View Components**:
   - `/components/dashboard/AdminDashboardView.tsx`
   - `/components/dashboard/FacultyDashboardView.tsx`
   - `/components/dashboard/StudentDashboardView.tsx`
   - `/components/dashboard/SubjectLeadDashboardView.tsx`
   - `/components/dashboard/DepartmentHeadDashboardView.tsx`
   - `/components/dashboard/AIInsightsStrip.tsx`
   - `/components/dashboard/ActivityTimeline.tsx`
   - `/components/dashboard/HealthDonutChart.tsx`

### Priority 3 - Feature Pages
Update remaining feature pages with light theme:
- Admin pages (users, academic-year, thresholds, co-library, po-pso, audit-log)
- Faculty pages (course management, marks, CO generation)
- Student pages (courses, marks, grievance)
- General pages (co-library, co-po-matrix, reports, settings)

### Priority 4 - Modals & Dialogs
- DeleteConfirmationDialog
- All feature-specific modals

## Color Mapping Reference

### From Dark → Light Theme

| Element | Old | New |
|---------|-----|-----|
| Background | `bg-cosmic` (#0F172A) | `bg-white` |
| Surface | `bg-[#1E293B]` | `bg-gray-50` or `bg-white` |
| Primary Text | `text-white` | `text-gray-900` |
| Secondary Text | `text-white/50` | `text-gray-600` |
| Tertiary Text | `text-white/30` | `text-gray-400` |
| Border | `border-white/10` | `border-gray-300` |
| Light Border | `border-white/5` | `border-gray-200` |
| Brand | `text-brand` | `text-blue-600` |
| Success | `text-attain` | `text-green-600` |
| Warning | `text-aurora` | `text-cyan-600` |
| Alert | `text-alert` | `text-red-600` |
| Hover BG | `hover:bg-white/5` | `hover:bg-gray-100` |

## Implementation Guidelines

### For Each Component File:

1. **Replace Background Colors**:
   - `bg-cosmic` → `bg-white`
   - `bg-[#0D1829]` → `bg-white`
   - `bg-[#1E293B]` → `bg-gray-50`
   - Generic dark backgrounds → `bg-white` or `bg-gray-50`

2. **Replace Text Colors**:
   - `text-white` → `text-gray-900`
   - `text-white/50` → `text-gray-600`
   - `text-white/30` → `text-gray-400`
   - `text-white/10` → `text-gray-200`

3. **Replace Border Colors**:
   - `border-white/10` → `border-gray-300`
   - `border-white/5` → `border-gray-200`
   - `border-white/20` → `border-gray-400`

4. **Replace Semantic Colors**:
   - Keep `text-brand` or replace with `text-blue-600`
   - `text-attain` → `text-green-600`
   - `text-aurora` → `text-cyan-600`
   - `text-alert` → `text-red-600`
   - `text-insight` → `text-purple-600`

5. **Add Subtle Shadows**:
   - Many elements should have `shadow-sm` or `shadow-md`
   - Dialogs should have `shadow-lg`

6. **Update Focus States**:
   - `focus:ring-brand` → `focus:ring-blue-500`
   - Update ring colors to match new theme

7. **Update Hover States**:
   - `hover:bg-white/5` → `hover:bg-gray-100`
   - `hover:border-white/30` → `hover:border-gray-400`

## Testing Checklist

- [ ] All text is readable (dark text on light backgrounds)
- [ ] Links are clearly distinguishable (blue)
- [ ] Buttons have proper contrast
- [ ] Hover states are visible
- [ ] Focus rings are visible and colored blue
- [ ] Modals have proper shadow/depth
- [ ] Cards have subtle borders or shadows
- [ ] Icons are visible (update gray icons where needed)
- [ ] Form inputs are clear
- [ ] Tables are easy to read (alternating rows if needed)
- [ ] Navigation is clear and organized
- [ ] Mobile view is responsive and readable

## Notes for Developers

1. **Avoid inline dark theme colors**: Don't use hardcoded colors like `#0D1829` or `#1E293B`
2. **Use CSS variables when possible**: Reference the variables defined in globals.css
3. **Maintain consistency**: All similar elements should use the same color scheme
4. **Test accessibility**: Ensure WCAG AA contrast ratios are met
5. **Preserve functionality**: Focus on styling, don't change component behavior
6. **University-appropriate**: This is an academic platform, keep design professional
7. **No cards/grids requirement**: Use flexbox and borders instead of card-based layouts
8. **Proper alignment**: Maintain consistent spacing and alignment throughout

## Implementation Order Recommendation

1. Complete all UI component files (2-3 files)
2. Update all dashboard components (6-8 files)
3. Update admin pages (7-8 files)
4. Update faculty pages (10+ files)
5. Update student pages (4-5 files)
6. Update remaining feature pages (15+ files)
7. Final QA and polish

## Resources

- Tailwind CSS color palette: https://tailwindcss.com/docs/customizing-colors
- Design system variables in: `/app/globals.css`
- Light theme colors defined in `@theme` section

---

**Status**: In Progress - 15% Complete
**Updated**: 2026-03-17
