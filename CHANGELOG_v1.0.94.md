# MultiChecker Pro v1.0.94

## UI Redesign Refresh

Version v1.0.94 focuses on visual interface refresh and usability improvements without changing existing functionality.

### Changed

- Updated color palette in clean security dashboard style.
- Increased default window size to 1440x900 and minimum size to 1180x760.
- Refreshed sidebar: cleaner brand block, navigation, language/theme/status cards.
- Refreshed tab header: larger titles and cleaner status indicator.
- Improved interface cards: larger radius, subtle borders, clearer visual hierarchy.
- Improved input and output areas: larger input area and log area.
- Improved action buttons and counters: softer radius and more consistent dashboard styling.

### Compatibility

- Existing tabs, buttons, exports, settings and handlers are preserved.
- Checker logic was not changed.
- Changes are UI/version only.

### Technical note

- main.py was restored after an accidental placeholder commit.
- v1.0.94 uses a runtime UI refresh loader over the stable v1.0.92 base commit.
