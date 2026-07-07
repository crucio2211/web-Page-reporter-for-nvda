# Page Reporter for NVDA

Page Reporter is an NVDA add-on that announces page load status and a quick summary of page structure after a web page loads in browse mode.

For example:

```text
Page loaded. Page has 3 headings, 47 links, 7 form fields, and 4 landmarks.
```

In brief report mode, Page Reporter speaks only the element summary:

```text
3 headings, 47 links, 7 form fields, and 4 landmarks.
```

The add-on is intended for real web browsers such as Google Chrome, Mozilla Firefox, Microsoft Edge, Brave, Opera, Vivaldi, and related browser builds. Version 3.0.2 and later avoid automatic "Page loaded" announcements from embedded browser surfaces inside apps such as Microsoft Teams, Spotify, Thunderbird, Slack, Discord, Outlook, Zoom, and Webex.

## Features

- Announces when a supported browser page finishes loading.
- Reports configurable counts for headings, links, form fields/buttons, and landmarks.
- Supports full report and brief report announcement modes.
- Lets users choose whether Page Reporter interrupts current NVDA speech before speaking.
- Supports dynamic sites and single-page apps where the visible page changes after navigation.
- Provides a manual recount command with `NVDA+Shift+R`.
- Provides a quick full report / brief report / off cycle with `NVDA+Shift+W`.
- Stores settings in Page Reporter's own JSON config instead of modifying NVDA's main configuration file.

## Settings

Open NVDA Preferences and choose the Page Reporter settings panel. From there you can:

- Enable or disable Page Reporter.
- Choose full report or brief report mode.
- Choose which element types are included in page summaries.
- Choose whether Page Reporter should interrupt current speech before its announcements.
- Disable reporting for specific domains, one domain per line.

## Localization

Page Reporter is ready for contributor translations using NVDA add-on gettext files.

Translator resources:

- Translation template: [`locale/pageReporter.pot`](locale/pageReporter.pot)
- Contributor guide: [`locale/README.md`](locale/README.md)

To add a language, copy the template to `locale/<language-code>/LC_MESSAGES/nvda.po`, translate the `msgstr` values, and add `locale/<language-code>/manifest.ini` for translated manifest text.

Keep placeholders unchanged while translating, including `%d`, `{elements}`, and `{lastElement}`.

## Documentation

The installed add-on documentation is available in:

- [`doc/readme.html`](doc/readme.html)
- [`doc/en/readme.html`](doc/en/readme.html)

## Version

Current version: 3.1.0
