# Light Theme Design System

## Visual Transformation

### Before: Dark Cosmic Theme
- **Background**: Deep space (#0F172A) with dark overlays
- **Text**: Bright white for contrast
- **Accents**: Neon-like brand, aurora, insight colors
- **Vibe**: Modern/tech startup aesthetic
- **Use Case**: Works for general audiences, modern apps

### After: Professional Light Theme
- **Background**: Clean white (#FFFFFF) with subtle gray accents
- **Text**: Dark gray (#1F2937) for professional appearance
- **Accents**: Professional blue (#2563EB) with semantic colors
- **Vibe**: Academic/institutional, trustworthy, professional
- **Use Case**: University platforms, educational software, institutional apps

## Color System Details

### Neutral Colors (Grayscale)
```
White:           #FFFFFF    - Backgrounds, cards
Off-white:       #F9FAFB    - Alternative backgrounds
Light Gray:      #F3F4F6    - Hover states
Gray:            #E5E7EB    - Borders
Medium Gray:     #D1D5DB    - Disabled states
Gray:            #9CA3AF    - Subtle text
Dark Gray:       #6B7280    - Secondary text
Darker Gray:     #1F2937    - Primary text/headings
```

### Brand Colors
```
Primary:         #2563EB    - Buttons, links, active states (Professional Blue)
Hover:           #1D4ED8    - Button hover state
Light BG:        #DBEAFE    - Light blue backgrounds
```

### Semantic Colors
```
Success:         #10B981    - Green for success states, completed tasks
Warning:         #F59E0B    - Amber for warnings, attention needed
Error:           #EF4444    - Red for errors, validation failures
Info:            #3B82F6    - Blue for informational messages
Aurora (Cyan):   #06B6D4    - Approval/status indicator
```

## Component Styling Guide

### Buttons

**Primary Button**
```
Background: #2563EB (Blue-600)
Text: White
Hover: #1D4ED8 (Blue-700)
Border: None
Padding: 12px 24px
Border-radius: 6px
Shadow: None (or subtle)
Focus: Ring blue-500
```

**Secondary Button**
```
Background: #F3F4F6 (Gray-100)
Text: #1F2937 (Gray-900)
Hover: #E5E7EB (Gray-200)
Border: 1px solid #E5E7EB
Padding: 12px 24px
Border-radius: 6px
Focus: Ring blue-500
```

**Danger Button**
```
Background: #EF4444 (Red-500)
Text: White
Hover: #DC2626 (Red-600)
```

### Input Fields

**Text Input**
```
Background: White
Border: 1px solid #E5E7EB
Text color: #1F2937
Placeholder: #9CA3AF
Hover border: #D1D5DB
Focus: 2px ring blue-500, border-blue-500
Padding: 10px 12px
Border-radius: 6px
```

**Select/Dropdown**
```
Same as text input
Arrow color: #6B7280
```

### Cards & Containers

**Standard Card**
```
Background: White
Border: 1px solid #E5E7EB
Padding: 16px
Border-radius: 8px
Shadow: 0 1px 2px rgba(0,0,0,0.05)
Hover: Border becomes #D1D5DB
```

**Surface Card**
```
Background: #F9FAFB (Gray-50)
Border: 1px solid #E5E7EB
Similar to standard card
```

### Navigation

**Navigation Bar**
```
Background: White
Border-bottom: 1px solid #E5E7EB
Text: #6B7280 (Gray-600)
Active link: #2563EB with bottom border
Hover: Color becomes #1F2937, border lightens
Height: 64px
```

**Navigation Item (Mobile)**
```
Background: White (normal), #F9FAFB (hover)
Text: #6B7280 (Gray-600)
Active: #2563EB with left border
Border-left: 3px solid #2563EB when active
```

### Modals & Dialogs

**Modal Backdrop**
```
Background: rgba(0, 0, 0, 0.4)
Blur: 4px (backdrop-blur-sm)
```

**Modal Container**
```
Background: White
Border: 1px solid #E5E7EB
Border-radius: 8px
Shadow: 0 10px 40px rgba(0,0,0,0.1)
Padding: 24px
```

**Modal Header**
```
Border-bottom: 1px solid #E5E7EB
Padding-bottom: 16px
Margin-bottom: 16px
```

### Tables

**Table Container**
```
Background: White
Border: 1px solid #E5E7EB
Border-radius: 8px
```

**Table Header**
```
Background: #F9FAFB (Gray-50)
Text: #1F2937 (Gray-900), bold
Border-bottom: 1px solid #E5E7EB
Padding: 12px
```

**Table Row**
```
Background: White (odd), #FFFFFF (even)
Hover: #F9FAFB (Gray-50)
Border-bottom: 1px solid #F3F4F6 (Gray-100)
Text: #1F2937 (Gray-900)
Padding: 12px
```

### Badges & Labels

**Badge - Primary**
```
Background: #DBEAFE (Blue-100)
Text: #1D4ED8 (Blue-700)
Padding: 4px 12px
Border-radius: 12px
```

**Badge - Success**
```
Background: #D1FAE5 (Green-100)
Text: #047857 (Green-700)
```

**Badge - Error**
```
Background: #FEE2E2 (Red-100)
Text: #DC2626 (Red-600)
```

## Typography

### Heading Styles

**H1 - Page Title**
```
Font: Display (Bricolage Grotesque)
Size: 48px - 64px (responsive)
Weight: 800
Color: #1F2937 (Gray-900)
Line-height: 1.1
```

**H2 - Section Title**
```
Font: Display
Size: 36px - 48px (responsive)
Weight: 700
Color: #1F2937
Line-height: 1.2
```

**H3 - Subsection**
```
Font: Sans (Plus Jakarta Sans)
Size: 24px - 28px (responsive)
Weight: 600
Color: #1F2937
```

**H4 - Minor Heading**
```
Font: Sans
Size: 18px - 20px (responsive)
Weight: 600
Color: #1F2937
```

### Body Text

**Regular Text**
```
Font: Sans (Plus Jakarta Sans)
Size: 14px - 18px (responsive)
Weight: 400
Color: #1F2937
Line-height: 1.6
```

**Secondary Text**
```
Same as regular
Color: #6B7280 (Gray-600)
```

**Caption**
```
Font: Mono (JetBrains Mono)
Size: 12px
Weight: 400
Color: #9CA3AF (Gray-400)
```

## Spacing System

The design uses consistent 4px baseline spacing:

```
xs:  2px
sm:  4px
md:  8px
lg:  16px
xl:  24px
2xl: 32px
3xl: 48px
4xl: 64px
```

### Padding Examples
- Small buttons: 8px 16px
- Standard inputs: 10px 12px
- Card padding: 16px
- Large sections: 24px - 32px

### Margin Examples
- Between sections: 24px - 32px
- Between elements: 8px - 16px
- Form field spacing: 16px

## Shadow System

```
None:    No shadow
Soft:    0 1px 2px rgba(0,0,0,0.05)
Medium:  0 4px 6px rgba(0,0,0,0.07)
Large:   0 10px 15px rgba(0,0,0,0.1)
Extra:   0 20px 25px rgba(0,0,0,0.15)
```

## Border Radius

```
None:     0px
Small:    4px
Medium:   6px
Large:    8px
Extra:    12px
Full:     9999px (circular)
```

**Usage**:
- Small controls: 4px
- Inputs/buttons: 6px
- Cards: 8px
- Rounded badges: 12px
- Avatars: 8px (or full for circular)

## Opacity Scale

For color variations:
```
100% or none: Full opacity
80% (/80):   Slightly faded
60% (/60):   Medium fade
40% (/40):   Significant fade
20% (/20):   Light
10% (/10):   Very light
```

## Interactive States

### Hover State
```
Button:       Darker color (primary → dark)
Link:         Underline + darker color
Card:         Subtle shadow increase or border darkening
Input:        Border darkens (gray-300 → gray-400)
Table row:    Background becomes gray-50
Navigation:   Text darkens, underline appears
```

### Focus State
```
All interactive: 2px ring in blue-500
Ring offset:     2px white space from element
```

### Active State
```
Navigation: Color becomes blue-600, border/underline shows
Toggle: Background becomes blue-600
Radio/Checkbox: Border and fill become blue-600
```

### Disabled State
```
Background:  Gray-100
Text:        Gray-400
Border:      Gray-200
Cursor:      not-allowed
Opacity:     50%
```

## Dark Mode (Optional)

When users enable dark mode, the system should:
1. Swap background colors (white ↔ dark gray)
2. Swap text colors (dark gray ↔ white)
3. Maintain color semantics (blue stays blue, green stays green)
4. Adjust borders and shadows appropriately

## Accessibility Guidelines

### Color Contrast
- Normal text: 4.5:1 ratio (WCAG AA)
- Large text: 3:1 ratio (WCAG AA)
- UI components: 3:1 ratio

### Focus Indicators
- Visible on all interactive elements
- Blue ring color (#3B82F6) at 2px width
- 2px offset from element

### Color Independence
- Never use color alone to convey information
- Use icons, text labels, or patterns alongside color
- Example: "Error (red)" not just red styling

## Implementation in Tailwind

All colors are available as Tailwind classes:

```tailwind
bg-white
bg-gray-50
bg-gray-100
text-gray-900
text-gray-600
border-gray-300
text-blue-600
bg-blue-50
hover:bg-gray-100
focus:ring-blue-500
```

## Design Tokens CSS Variables

In `/app/globals.css`:

```css
--color-background: #FFFFFF
--color-surface: #F9FAFB
--color-text-primary: #1F2937
--color-text-secondary: #6B7280
--color-brand: #2563EB
--color-success: #10B981
--color-warning: #F59E0B
--color-error: #EF4444
```

Usage: `background-color: var(--color-background);`

## Quality Assurance Checklist

- [ ] All text meets contrast requirements
- [ ] All buttons have visible hover/focus states
- [ ] All inputs have visible focus indicators
- [ ] Navigation is clear and consistent
- [ ] Modals have proper depth (shadow)
- [ ] Semantic colors are used consistently
- [ ] Spacing is consistent throughout
- [ ] Icons are visible against backgrounds
- [ ] Mobile view is responsive
- [ ] Color palette matches brand identity

---

**Design System Version**: 1.0 Light Theme
**Last Updated**: 2026-03-17
**Framework**: Tailwind CSS v4
**Color Mode**: Light (Dark mode optional)
