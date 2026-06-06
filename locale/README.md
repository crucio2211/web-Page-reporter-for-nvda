# Page Reporter localizations

Page Reporter uses NVDA add-on gettext localization. Contributor translations live in the `locale` folder and are loaded automatically by NVDA when the add-on is installed.

## Folder layout

Use this structure for each language:

```text
locale/
  <language-code>/
    LC_MESSAGES/
      nvda.po
    manifest.ini
```

Examples:

```text
locale/fr/LC_MESSAGES/nvda.po
locale/fr/manifest.ini
locale/fil/LC_MESSAGES/nvda.po
locale/fil/manifest.ini
```

Use NVDA's language codes where possible. For example, `fr` for French, `es` for Spanish, and `fil` for Filipino.

## Translating add-on messages

1. Copy `pageReporter.pot` to `locale/<language-code>/LC_MESSAGES/nvda.po`.
2. Edit the new `nvda.po`.
3. Fill in the `Language` header and each `msgstr`.
4. Keep placeholders exactly as they appear, such as `%d`, `{elements}`, and `{lastElement}`.
5. If your language has plural forms, add the correct `Plural-Forms` header and translate all plural entries.

NVDA compiles `.po` files into `.mo` files during the add-on build process. Do not edit generated `.mo` files by hand.

## Translating the manifest

Create `locale/<language-code>/manifest.ini` and translate these fields:

```ini
summary = Page Reporter
description = Announces page load status and element summary after a web page loads in browse mode. Toggle with NVDA+Shift+W. Configure in NVDA Preferences.
```

Do not translate technical fields such as `name`, `version`, `minimumNVDAVersion`, or `lastTestedNVDAVersion`.

## Updating the template

When new user-facing strings are added to `globalPlugins/pageReporter.py`, update `locale/pageReporter.pot` so translators can pick them up.

Strings shown to users should be wrapped in `_()`. Counted nouns should use `ngettext()` so languages with plural rules can translate them correctly.
