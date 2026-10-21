# Cún Zoom — desktop design system, v1.1

## Product decision

The first screen answers “which class is next, and what can I do with it?” Calendar rows carry the interface. A selected row has a detail inspector; the library uses a list and document reader. Recording controls show received data, rather than a decorative waveform or a simulated success state.

This is an application redesign, not a marketing page. Use Hallmark's Index-First composition and Cobalt palette as a desktop variant: restrained blue, cool neutral surfaces, fine rules, aligned time columns. Retain the existing loopback API, DPAPI configuration and local folders.

## Sources and interpretation

- [Hallmark](https://github.com/Nutlope/hallmark): hierarchy, named tokens, restrained composition and state discipline. Application controls replace marketing archetypes; no promotional hero or invented metrics.
- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): Calendar & Scheduling / Productivity recommendations, Swiss minimalism, keyboard operation, contrast, errors and responsive review. Reference only; no third-party executable installed.
- [Granola](https://docs.granola.ai/help-center/getting-started/granola-101): meeting-first navigation and persistent notes.
- [Otter](https://help.otter.ai/hc/en-us/articles/360049722894-Otter-Quick-Start-Guide): conversations, folders and transcript context.
- [Fathom](https://help.fathom.video/en/articles/13926529): separating summary and transcript views. No third-party branding or cloud functionality copied.

## Shared language

Four destinations: Lịch học / Bài giảng / Ghi bài / Cài đặt. A single active destination, URL hash and browser history agree. Ctrl+K searches the same destinations, real calendar entries and local lessons. Opening a search result never joins a class or starts recording.

Calendar title/code/group comes from the actual event title. Do not infer a missing room, date, group or location. Counts come from the service, not fixtures. Empty, disconnected and paused states remain distinct.

Recording states: SDK checked is not a joined classroom; joined is not host recording permission; recording is not confirmed until audio bytes arrive. No invented waveform, captured slides or progress percentage.

## Tokens and assets

`tokens.css` is canonical. `web/tokens.css` is its packaged copy, refreshed by the build. Do not modify only the copy. Colors are semantic OKLCH roles, with independent dark mappings. The accent is functional blue, never a gradient. Red and green carry accompanying status text.

Space Grotesk: headings. Inter: body and controls. JetBrains Mono: actual time/data values. Fonts are local assets, never fetched during application use. OFL license notices ship in `web/fonts/`.

4-point spacing rhythm: 4, 8, 12, 16, 24, 32, 48, 64px. Controls have a 44px minimum height. Inputs, adjacent buttons and search share the same base. Borders remain 1px across states; focus uses an immediate 2px outline. Content rows and document titles may wrap because they contain user data, while fixed navigation/action labels stay on one line.

Light and dark surfaces, muted text, accent fill/ink and error/success pairs must be checked separately. Subtle rules separate groups; input boundaries and focus rings use stronger contrast. No shadows needed for ordinary content.

## Layout and interaction

- Desktop: 216px sidebar, 64px header, flexible agenda, 264–300px inspector.
- Below 950px: inspector moves under the agenda. Library reader stacks after the list.
- Below 650px: compact top navigation; calendar filters stack; settings and room forms become one column.
- Source scope is 14 upcoming days. Week and day controls filter only that available scope; earlier weeks may contain no source data.
- Native dialog provides focus containment and Escape. Search results support arrows and Enter, restore trigger focus on close.
- Settings/document tabs use native buttons, selected state and arrow/Home/End navigation.
- Polls hydrate settings once; they must not overwrite edited fields. Form failures retain values and focus an inline error. Secrets are never stored in browser storage.
- Motion is limited to feedback and toast appearance; reduced-motion removes transitions. No automatic animation, entrance choreography or hover scaling.

## Token interoperability

Runtime uses plain CSS, not Tailwind or shadcn. These mappings are for a future migration, not additional runtime dependencies.

### CSS
```css
/* Use the canonical file, do not duplicate numeric palette values. */
@import './tokens.css';
.surface { background: var(--color-paper); color: var(--color-ink); }
```

### Tailwind 4
```css
@theme inline {
  --color-background: var(--color-paper);
  --color-foreground: var(--color-ink);
  --color-primary: var(--color-accent);
  --color-primary-foreground: var(--color-accent-ink);
  --font-sans: var(--font-body);
  --font-heading: var(--font-display);
}
```

### DTCG mapping
```json
{
  "surface": { "$type": "color", "$value": { "colorSpace": "oklch", "components": [0.99, 0.002, 250] } },
  "accent": { "$type": "color", "$value": { "colorSpace": "oklch", "components": [0.49, 0.19, 260] } },
  "controlHeight": { "$type": "dimension", "$value": { "value": 44, "unit": "px" } }
}
```

### shadcn semantic mapping
```css
:root {
  --background: var(--color-paper);
  --foreground: var(--color-ink);
  --primary: var(--color-accent);
  --primary-foreground: var(--color-accent-ink);
  --muted: var(--color-paper-2);
  --muted-foreground: var(--color-muted);
  --border: var(--color-rule);
  --input: var(--color-rule-2);
  --ring: var(--color-focus);
}
```

## Verification and limits

Review the four views at 320, 375, 414, 768, 1024 and 1440px. Test filtering, preparing a room, keyboard search, tabs, dirty settings, native form errors, safe document rendering and both color modes. Keep synthetic lesson fixtures under `build/`, distinctly labeled and excluded from source publication and the executable.

Do not count a passed SDK check as a real lecture recording test. A live class and host recording permission remain external dependencies. The new UI does not expand recording or network access.
