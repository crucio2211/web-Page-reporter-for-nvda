# Page Reporter — NVDA Add-on

**Version:** 2.5.0
**Authors:** Rosendo Barde Hubilla Jr. and Joseph Bautista
**Minimum NVDA Version:** 2019.3
**Last Tested NVDA Version:** 2026.1

---

## Description

Page Reporter is an NVDA add-on that automatically announces a summary of page elements — including headings, links, buttons, form fields, and landmarks — each time a web page finishes loading. This helps screen reader users quickly understand the structure and content of a page without having to manually navigate through it.

---

## Features

- Announces page element counts on every page load across major browsers (Chrome, Firefox, Brave, Edge)
- Supports single-page application (SPA) navigation on sites like YouTube and Facebook
- Configurable — choose which element types to report
- Per-site blocking — disable reporting for specific websites
- Toggle on/off anytime with **NVDA+Shift+W**

---

## Installation

1. Download the latest `.nvda-addon` file from the [Releases](../../releases) page.
2. Open NVDA, go to **Tools → Manage add-ons**.
3. Click **Install**, then browse to the downloaded `.nvda-addon` file.
4. Restart NVDA when prompted.

---

## Usage

Once installed, Page Reporter works automatically in the background. When a web page finishes loading in your browser, NVDA will announce a summary such as:

> *Page loaded. Page has 12 headings, 47 links, 3 buttons, and 2 landmarks.*

### Keyboard Shortcut

| Gesture | Action |
|---|---|
| NVDA+Shift+W | Toggle Page Reporter on or off |

---

## Configuration

Go to **NVDA Preferences → Settings → Page Reporter** to configure:

- **Enable/Disable** Page Reporter
- **Choose which elements to report:** Headings, Links, Buttons, Form Fields, Landmarks
- **Blocked sites:** Enter domain names (one per line) to disable reporting on specific sites (e.g. `mail.google.com`)

---

## Compatibility

| Browser | Supported |
|---|---|
| Google Chrome | ✅ |
| Mozilla Firefox | ✅ |
| Microsoft Edge | ✅ |
| Brave | ✅ |
| Other Chromium-based browsers | ✅ |

---

## License

This add-on is licensed under the [GNU General Public License version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).

---

## Changelog

### Version 2.5.0
- Improved stability and duplicate announcement prevention
- Fixed busy:true retry logic for Facebook and heavy SPAs
- Last-wins cancellation system for rapid page navigation
- Improved SPA navigation detection for YouTube and Facebook

### Version 2.0.0
- Added SPA navigation support (YouTube, Facebook, Twitter)
- Non-blocking chunked COM tree walk to prevent NVDA freezing
- virtualBuffer fast path for zero-COM role extraction
- Per-treeInterceptor cancellation tokens

### Version 1.0.0
- Initial release
