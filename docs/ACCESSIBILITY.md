Accessibility Checklist — Soft Systems Studio
===========================================

Quick, actionable items to keep this site accessible and easy to scan.

- Skip link: `website/index.html` now includes a visible skip link for keyboard users.
- Landmarks & roles: ensure `header` has `role="banner"`, `nav` has `role="navigation"` and `main` has `role="main` — already added.
- Focus styles: we added a visible focus outline for keyboard users; keep these present when changing styles.
- Images: always include meaningful `alt` text. Decorative images may use empty `alt=""`.
- Color contrast: check CTA buttons and text against WCAG AA. The lime gradient is high-contrast on dark backgrounds, but verify with tools.
- Keyboard navigation: test the page with Tab-only navigation and ensure all interactive elements receive focus in a logical order.
- ARIA usage: avoid unnecessary ARIA; prefer semantic HTML. When using ARIA, validate attributes are correct and IDs referenced exist.
- Forms: ensure labels are associated with inputs (`<label for=>`) and error states are descriptive.
- Automated checks: add `axe-core` or `pa11y` in CI to surface regressions.

Recommended next steps
- Add a CI step that runs `axe` against the built `build/index.html` (or a deployed preview) to catch regressions automatically.
- Run manual keyboard walkthroughs and a color-contrast scan on key pages (home, platform, pricing).
