# Changelog (English)

> English summary of recent releases. The full historical changelog is in [CHANGELOG.md](CHANGELOG.md).
> [中文](CHANGELOG.md) | English

## v0.28.14

- Language selector buttons now flex to the panel width and align with the Game Library button.
- Removed temporary i18n diagnostic DOM attributes.

## v0.28.6

- i18n observer diagnostics and mount retry for the real UI document.
- 555 tests passed.

## v0.28.5

- Cross-realm `root.nodeType` scan fix so QAM text nodes are translated.

## v0.28.4

- Cross-document TreeWalker/MutationObserver/timer use `ownerDocument` + `defaultView`.

## v0.28.3

- i18n observer starts from the mounted root ref instead of module load.

## v0.28.2

- Full 434-entry dictionary: 235 direct Chinese strings + 199 `\uXXXX`-escaped strings.

## v0.28.1

- Fixed English not applying: escaped Chinese strings were missing from the dictionary.

## v0.28.0

- First-launch language selection: 中文 / English.
- Language persisted in `localStorage["freedeckcy.language"]`.
- QAM/settings/native library/detail translation layer; switchable from QAM home.

## v0.27.20

- Leftmost card focus ring fully visible; shelf scroll-snap/anchor fixes.
- 555 tests passed.

For v0.27.0 and earlier, see the Chinese [CHANGELOG.md](CHANGELOG.md).
