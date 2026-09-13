---
name: uConsole Terminal UI
colors:
  surface: '#081425'
  surface-dim: '#081425'
  surface-bright: '#2f3a4c'
  surface-container-lowest: '#040e1f'
  surface-container-low: '#111c2d'
  surface-container: '#152031'
  surface-container-high: '#1f2a3c'
  surface-container-highest: '#2a3548'
  on-surface: '#d8e3fb'
  on-surface-variant: '#c6c6cd'
  inverse-surface: '#d8e3fb'
  inverse-on-surface: '#263143'
  outline: '#909097'
  outline-variant: '#45464d'
  surface-tint: '#bec6e0'
  primary: '#bec6e0'
  on-primary: '#283044'
  primary-container: '#0f172a'
  on-primary-container: '#798098'
  inverse-primary: '#565e74'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#45dfa4'
  on-tertiary: '#003825'
  tertiary-container: '#001c10'
  on-tertiary-container: '#009367'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#68fcbf'
  tertiary-fixed-dim: '#45dfa4'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#081425'
  on-background: '#d8e3fb'
  surface-variant: '#2a3548'
typography:
  headline-lg:
    fontFamily: JetBrains Mono
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.05em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  margin: 1rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system channels a sleek, dark embedded Linux aesthetic tailored specifically for portable terminal hardware. The brand personality is technical, focused, and high-performance, evoking the spirit of custom-compiled kernels and retro-futuristic hacker culture. 

The visual style merges **Glassmorphism** with **Minimalism**, utilizing translucent, frosted layers over deep, monochrome slate backdrops to create physical depth on compact screens. Vibrant, customizable hue accents cut through the dark interface to provide critical status feedback and visual distinction. Typography is crisp, monospaced-adjacent, and uncompromisingly legible, ensuring high contrast for outdoor readability under varied lighting conditions. The emotional response is one of absolute control, precision, and elite technical competence.

## Colors

The color palette is anchored by deep monochrome slate shades that minimize light emission and reduce eye strain in low-light environments while preserving extreme contrast ratios for outdoor legibility. 

- **Primary (`#0F172A`):** Deep obsidian slate used for the primary canvas background.
- **Secondary (`#38BDF8`):** Electric terminal cyan serving as the primary interactive accent and focus state.
- **Tertiary (`#34D399`):** Phosphor green used exclusively for success states, active system processes, and terminal prompts.
- **Neutral (`#1E293B`):** Surface slate for elevated containers, panels, and frosted glass components.

Surface layers rely on subtle opacity shifts of the neutral palette combined with backdrop blurring to delineate interface boundaries rather than heavy borders.

## Typography

Typography is strictly monospaced to reinforce the embedded Linux terminal metaphor. **JetBrains Mono** is utilized across all levels, ensuring code, system logs, metadata, and standard UI copy share a unified, highly legible grid alignment. 

Sizes are deliberately compressed to maximize information density on small form-factor displays. Headlines over 28px feature mobile-specific downscaling to prevent layout clipping. Letter spacing on labels is slightly widened (`0.05em`) to enhance legibility at small sizes under bright outdoor conditions.

## Layout & Spacing

The layout employs a compact, density-optimized fluid grid system designed for hardware with restricted screen real estate. A 12-column structure with tight 12px (`0.75rem`) gutters and 16px (`1rem`) outer margins maximizes usable viewport area.

Spacing scales are intentionally condensed (`space-xs` starting at 2px) to accommodate dense streams of system telemetry, log outputs, and modular control panels. On mobile and handheld form factors, panels reflow into single-column vertical stacks with collapsible accordion sections to maintain touch and directional-pad accessibility.

## Elevation & Depth

Depth is established primarily through **Glassmorphism** and low-contrast tonal layering rather than heavy drop shadows. 
- **Translucent Surfaces:** Elevated cards and panels use semi-transparent neutral slates (`#1E293B` at 75% opacity) paired with a robust backdrop blur (`blur(12px)`) to separate foreground tools from the deep primary background.
- **Outlines & Borders:** Elements utilize subtle "ghost borders" (1px strokes of `#38BDF8` at 20% opacity) that brighten on focus or hover.
- **Ambient Glows:** Active or targeted components emit a faint, diffused cyan or green box-shadow to simulate backlit hardware indicators and CRT phosphor glow.

## Shapes

A controlled **Soft** shape language (`roundedness` level 1) is employed. UI containers feature a minimal 0.25rem corner radius, preserving a precise, engineered aesthetic reminiscent of rack-mounted hardware and terminal windows, while avoiding harsh 90-degree points that can catch the eye awkwardly on high-PPI miniature displays. Larger containers and modal windows scale up to 0.5rem (`rounded-lg`), maintaining structural integrity across all components.

## Components

### Buttons
Buttons feature a translucent frosted background with a crisp 1px accent border. In default states, text and icons render in high-contrast neutral-light. Hover or focus states trigger a solid electric cyan (`#38BDF8`) fill with dark slate text, providing instantaneous tactile feedback for hardware d-pad or keyboard navigation.

### Chips & Tags
Compact, pill-shaped or softly rounded indicators used for status tags (e.g., `ONLINE`, `CPU: 42%`, `SECURE`). They utilize semi-transparent tertiary or secondary background fills with matching high-contrast text and a 1px solid tonal border.

### Lists & Telemetry Feeds
Designed for high-density data display. Rows feature alternating subtle background opacity shifts for scannability. Monospaced text aligns cleanly into tabular columns, optimized for live-updating system logs and network packet monitors.

### Checkboxes & Radio Buttons
Customized to mimic command-line options. Unchecked states display as hollow square or circular wireframes in neutral slate. Checked states fill entirely with the active phosphor green or cyan accent, accompanied by a sharp internal glyph or dot.

### Input Fields
Command line style inputs featuring a solid dark slate background, a 1px translucent border that solidifies upon focus, and a blinking underscore or block cursor to emulate an active terminal prompt. Placeholder text is styled in muted gray, with user input rendering in bright secondary cyan.

### Cards & Panels
Frosted glass containers used to group modular system controls, network interfaces, and performance graphs. Each card includes a subtle header bar complete with a status indicator light and minimize/maximize utility icons.

### Additional Components: Terminal Output Box
A dedicated scrollable container optimized for raw shell output, featuring auto-scrolling behavior, color-coded ANSI stream support, and a quick-copy action trigger.