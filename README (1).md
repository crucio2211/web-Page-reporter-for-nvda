# Page Reporter — NVDA Addon

**Version 2.6.1** | By Rosendo Barde Hubilla Jr. and Joseph Bautista

Page Reporter automatically announces a summary of page elements every time a web page finishes loading in browse mode. Instead of manually navigating around to find out what's on the page, NVDA tells you right away.

**Example announcement:**
> Page loaded. Page has 3 headings, 47 links, 5 buttons, 2 form fields, and 4 landmarks.

It also works on single-page applications like Facebook, YouTube, Twitter/X, and Reddit — every time you navigate to a new section and the URL changes, Page Reporter will announce the updated element summary automatically.

---

## Features

- Automatic page element summary on every page load in browse mode
- SPA (single-page application) support — detects URL/title changes on YouTube, Facebook, Reddit, X, etc.
- Fully configurable — choose which element types to include in the announcement
- Per-site blocking — silence the addon on specific domains
- Lightweight — no announcements for background tabs or when focus is outside the browser
- Settings saved to a standalone JSON file (`%APPDATA%\nvda\pageReporter.json`), completely isolated from NVDA's own config

---

## Requirements

- NVDA 2019.3 or later
- Tested up to NVDA 2026.1

---

## Installation

1. Download the latest `.nvda-addon` file from the [Releases](../../releases) page.
2. Open the file — NVDA will prompt you to install it.
3. Restart NVDA when asked.

To uninstall, go to **NVDA menu → Tools → Manage Add-ons**, select Page Reporter, and press **Remove**.

---

## Keyboard Shortcut

| Gesture | Action |
|---|---|
| `NVDA+Shift+W` | Toggle Page Reporter on or off |

NVDA will say "Page Reporter on" or "Page Reporter off" to confirm.

---

## Settings

Open Page Reporter settings via **NVDA menu → Preferences → Settings → Page Reporter**.

### Enable Page Reporter
Master on/off switch. Can also be toggled quickly with `NVDA+Shift+W`.

### Report these elements
Choose which element types are included in the announcement. Each can be turned on or off independently.

| Element | What is counted |
|---|---|
| Headings | H1 through H6 heading elements |
| Links | All clickable links |
| Buttons | Buttons and menu buttons |
| Form fields | Text inputs, checkboxes, radio buttons, and combo boxes |
| Landmarks | ARIA landmark regions — navigation, main, banner, search, etc. |

If none of the enabled element types are found on the page, NVDA will simply say **"Page loaded."**

### Disabled sites
Enter domain names (one per line) where Page Reporter should stay silent. For example, entering `youtube.com` will silence it on all YouTube pages, including subdomains like `music.youtube.com`. You do not need to include `www.` — the base domain is enough.

All settings are saved automatically when you press **OK** in the NVDA Settings dialog.

---

## Supported Browsers

Works in any browser that NVDA supports in browse mode:

- Google Chrome
- Mozilla Firefox
- Microsoft Edge
- Brave
- Any other Chromium or Gecko-based browser NVDA can browse in

---

## Known Limitations

- Pages that update content without changing the URL (such as infinite scroll feeds) will not trigger a new announcement.
- On heavily scripted pages, the announcement may appear a few seconds after the page loads while the addon waits for the page to finish rendering.
- Page Reporter only works in browse mode. Application mode (used in some web apps like Gmail) is not supported.

---

## Changelog

### v2.6.1
- Fixed: Repeated announcements when tabs load in the background or when focus is outside the browser. The addon now correctly checks whether the loaded page is the active, foreground treeInterceptor before announcing.

### v2.6.0
- Settings moved to a standalone JSON file (`%APPDATA%\nvda\pageReporter.json`), completely isolated from NVDA's own `nvda.ini`. No more risk of corrupting NVDA config on save.
- Toggle (`NVDA+Shift+W`) no longer triggers NVDA config save.

### v2.5.x
- Added SPA (single-page application) URL watcher for YouTube, Facebook, Reddit, and similar sites.
- Added busy-state retry with exponential back-off for heavily scripted pages.
- Added non-blocking chunked COM tree walk to avoid freezing NVDA on large pages.
- Added virtualBuffer fields fast path for faster element counting.

### v2.4.0
- Initial public release.
- Automatic page element summary on browse mode page load.
- Configurable element types and per-site blocking.
- NVDA+Shift+W toggle.

---

## Authors

Rosendo Barde Hubilla Jr. and Joseph Bautista

---

## License

This addon is distributed under the [GNU General Public License v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html), the same license used by NVDA itself.
