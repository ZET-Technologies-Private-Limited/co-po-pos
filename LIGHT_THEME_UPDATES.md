# Light Theme Conversion Guide

## Completed Updates
- ✅ globals.css - Already has light theme variables
- ✅ layout.tsx - Already configured for light theme
- ✅ Student Dashboard Page - Updated to light theme
- ✅ Faculty Dashboard Backend View - Updated to light theme (partial)

## Color Mapping - Dark to Light

### Text Colors
- `text-white` → `text-gray-900` (primary text)
- `text-white/50` → `text-gray-600` (secondary text)
- `text-white/30` → `text-gray-700` (tertiary text)
- `text-white/20` → `text-gray-500` (muted text)
- `text-white/40` → `text-gray-700` (body text)

### Background Colors
- `bg-cosmic` → `bg-white`
- `border-white/10` → `border-gray-300`
- `border-white/20` → `border-gray-300`
- `border-white/5` → `border-gray-200`
- `bg-white/[0.02]` → `bg-gray-50`
- `bg-white/5` → `bg-blue-50`
- `hover:bg-white/5` → `hover:bg-gray-50`

### Semantic Colors (Keep)
- `text-brand` → Stays `text-blue-600` (or `text-blue-700` for darker)
- `text-alert` → `text-red-600`
- `text-attain` → `text-green-600`
- `text-warning` → `text-amber-600`
- `border-brand` → `border-blue-300`

### Component Styling
```tailwind
/* Old Dark */
className="border border-white/10 bg-white/[0.02] px-4 py-3"
className="text-white"

/* New Light */
className="border border-gray-300 bg-white px-4 py-3"
className="text-gray-900"
```

## Files Still Needing Updates

### Priority 1: Core Pages
- [ ] `frontend/frontend/src/app/(auth)/login/page.tsx` - Login page (CRITICAL)
- [ ] `frontend/frontend/src/components/dashboard/AdminDashboardView.tsx` - Admin dashboard
- [ ] `frontend/frontend/src/components/dashboard/StudentDashboardView.tsx` - Student dashboard
- [ ] `frontend/frontend/src/components/dashboard/SubjectLeadDashboardView.tsx` - Lead dashboard
- [ ] `frontend/frontend/src/components/dashboard/DepartmentHeadDashboardView.tsx` - HOD dashboard

### Priority 2: Shared UI Components
- [ ] `frontend/frontend/src/components/ui/DataTable.tsx`
- [ ] `frontend/frontend/src/components/ui/FormInput.tsx`
- [ ] `frontend/frontend/src/components/ui/ProfileMenu.tsx`
- [ ] `frontend/frontend/src/components/ui/NotificationsPanel.tsx`
- [ ] `frontend/frontend/src/components/ui/ToastContainer.tsx`

### Priority 3: Course/Features
- [ ] `frontend/frontend/src/components/courses/COCard.tsx`
- [ ] `frontend/frontend/src/components/courses/MatrixGrid.tsx`
- [ ] `frontend/frontend/src/components/courses/NetworkGraph.tsx`
- [ ] `frontend/frontend/src/components/courses/AttainmentBarChart.tsx`
- [ ] `frontend/frontend/src/components/courses/AttainmentRadarChart.tsx`

### Priority 4: Remaining Pages
- All other pages in `/app/(app)/` folders

## Update Strategy

For each file:
1. Search for dark color references
2. Apply light theme mappings above
3. Test in browser for readability
4. Ensure semantic colors remain distinct
5. Verify light theme is professional and impressive

## Design Standards
- Primary Text: `text-gray-900`
- Secondary Text: `text-gray-600`
- Borders: `border-gray-300` (primary), `border-gray-200` (subtle)
- Backgrounds: `bg-white`, `bg-gray-50`, `bg-gray-100`
- Hover States: `hover:bg-gray-50`, `hover:border-gray-400`
- Focus States: `focus:ring-2 focus:ring-blue-500`

## Accessibility
- Ensure all text has 4.5:1 contrast ratio
- Maintain semantic color meanings (red=error, green=success)
- Keep icon colors consistent with text colors
- Verify dark text on light backgrounds everywhere

