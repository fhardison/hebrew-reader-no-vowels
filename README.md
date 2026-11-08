# No Vowel biblical Hebrew reader

This is a reader for biblical Hebrew without vowels, but the vowel pointings, gloss, lemma, and parse are shown on mouse over. 


Oct 2026: Claude Code was used to improve the layout and presentation of the parsing information.

# Offline use (PWA)

The site in `docs/` is served by GitHub Pages and works as an installable, offline Progressive Web App.

- **Download all** (toolbar at the top of every page) saves every book (~50 MB) to the device. Installing the app to the home screen starts this automatically.
- **Update** clears the offline copy and downloads everything again from the server. The new copy is downloaded alongside the old one and only replaces it once every file has arrived, so a failed update never leaves you without a working copy.
- The toolbar says **Update available** when the server's `docs/files.json` version differs from the downloaded one.

`build_reader.py` writes the pages and `docs/files.json` (the list of offline files plus a version hash). If you edit `docs/pwa.js`, `docs/manifest.webmanifest` or the icons, re-run `python build_reader.py` so the version changes. `docs/sw.js` is deliberately static.

# License


since the MACULA Hebrew LInguistic Datasets are licensed under a [CC By 4.0](http://creativecommons.org/licenses/by/4.0/), this repo is too.

