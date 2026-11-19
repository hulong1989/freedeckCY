# Changelog (English)

> English summary of recent releases. The full historical changelog is in [CHANGELOG.md](CHANGELOG.md).
> [中文](CHANGELOG.md) | English

## v0.28.15

### Range resume probe

- New `probe_resume_support()`: sends `Range: bytes=0-0` to the direct URL and decides resume support from headers only (206 / `Content-Range` / `Accept-Ranges: bytes` supported; 200 without range headers unsupported; errors, other statuses and invalid URLs conservatively assume supported).
- Recovery/rechain paths probe once when partial data exists: supported keeps progress via `changeUri`; unsupported logs `resume unsupported`, quarantines the partial file and restarts from zero instead of stalling on invalid retries.
- Normal downloads issue no extra request; results are logged for line troubleshooting.
- 10 new tests cover the four probe outcomes, error fallback, header merging, and both recovery branches; 585 tests passed.

## v0.28.14

### Install reliability

- **Installed-game verify/repair**: checks the install folder, main executable/ROM and Steam shortcut item by item; one click rebuilds the shortcut, Proton mapping and four-piece artwork; missing files are reported as requiring a reinstall instead of a fake success.
- **Full health check**: scans every installed game and summarizes OK / needs repair / needs reinstall in the library top bar, with one click to repair every repairable item (reinstall-required ones excluded).
- **Failure diagnostics**: failed tasks expose stage (resolve/download/extract/install), reason, suggestions, and whether retry/fallback is possible.
- **Source fallback**: retry a failed task on the other Tianyi/Baidu source for the same game; retrying on the current source falls back automatically once when the direct link cannot be re-fetched.
- **Pre-install environment preflight**: checks download/install folder writability and free space (512MB floor), available on the new Settings "Environment" tab; the install confirmation shows failed checks and changes the button to "Download Anyway".
- Non-Steam games without a logo fall back to portrait/landscape artwork.
- 20 new reliability tests; 574 tests passed.

### UI

- Language selector buttons flex to the panel width and align with the Game Library button.
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
