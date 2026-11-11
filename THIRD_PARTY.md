# Third-party material

The code in this repository is under the MIT licence (`LICENSE`). The material below comes from others and keeps its
own terms. If you hold rights in anything listed here and want it credited differently or removed, please open an issue.

## Included in the repository

| Path | Source | Terms |
|---|---|---|
| `data/corpora/` | Project Gutenberg texts (language models), Gutenberg headers kept | Public domain in the USA; Project Gutenberg licence for the files |
| `data/corpora/extra/*_wiki.txt` | Wikipedia article extracts (Russian so far), `scripts/fetch_wiki_corpora.py`; not redistributed | CC BY-SA 4.0 |
| `data/corpora/extra/` | Project Gutenberg books in 16 more languages (also el, ru, bg, he), downloaded by `scripts/fetch_corpora.py` (ids in `data/sources/corpora_extra.json`); not redistributed | Public domain in the USA; Project Gutenberg licence |
| `data/sources/key_*.txt`, `declaration.txt`, `beale_try8` | Public-domain texts used as book-cipher keys (US founding documents, King James Bible, Shakespeare, Smith, Paine, FitzGerald), the Beale pamphlet via Wikisource | Public domain |
| `data/sources/wp_*.txt`, `data/sources/research/`, `data/sources/scripts/` (`sources.json` lists titles, URLs and dates) | Wikipedia article text | CC BY-SA 4.0: attribution to Wikipedia contributors; share-alike applies to these files |
| `data/sources/langid/` (`sources.json`) | Wikipedia article introductions in 50 languages, for language identification | CC BY-SA 4.0 |
| `data/sources/glosses/` (`sources.json`) | Wiktionary lemma pages for Egyptian, Mycenaean Greek and Old Norse | CC BY-SA 4.0 |
| `data/sources/benchmark/`, `data/sources/unsolved/`, `data/sources/zodiac/` | Cipher transcriptions from the AZdecrypt collection, https://github.com/doranchak/azdecrypt (David Oranchak and contributors), and the sources named on each case page | See the AZdecrypt repository; the ciphertexts are historical documents or published challenges |
| `data/sources/vms_ZL3b-n.txt`, `vms_stolfi.evt` | Voynich manuscript transliterations: Zandbergen and Landini (voynich.nu), Stolfi and Landini (EVT interlinear) | Distributed freely by their authors for study, with attribution |
| `data/sources/scripts_lab/` | Rongorongo, Linear A and Liber Primus sign data (sources in each file and on the case pages) | See each source |
| `data/sources/figaro/*_transcription.json`, `letter_digit_family.json`, `ocr*.json` | This project's own transcriptions and OCR of 19th-century Le Figaro personal-column ads (the newspapers are in the public domain; scans as published in Didier Müller's database and BnF Gallica) | Transcriptions: MIT with the code |
| `codebreaker/web/static/recovery/` | Crops of those 19th-century newspaper scans | Public domain originals |
| `codebreaker/web/static/fonts/` | Noto Sans Runic and Noto Sans Ogham (Google), see the README there | SIL Open Font License 1.1 (`OFL.txt`) |
| `data/sources/sounds/sources.json` | Lists Wikimedia Commons bird recordings (audio not included) | CC BY-SA, per recording |

## Downloaded, not redistributed

`scripts/fetch_sources.py` downloads these from their public sites; they are listed in `.gitignore`.

| File | Source |
|---|---|
| `data/sources/figaro/codes.html` | Didier Müller, *Petites annonces du Figaro*, table of cipher systems: https://www.apprendre-en-ligne.net/crypto/Figaro/codes.php |
| `data/sources/figaro/ads.json` | The same database's ad index, built by `scripts/figaro_harvest.py` |
| `data/sources/research/schmeh50.html` | Klaus Schmeh, *The top 50 unsolved encrypted messages*: https://scienceblogs.de/klausis-krypto-kolumne/the-top-50-unsolved-encrypted-messages/ |

Papers used during the work are cited, not copied: Dunin, Müller and Schmeh, *French encrypted newspaper advertisements in
the 19th century*, HistoCrypt 2024 (https://ecp.ep.liu.se/index.php/histocrypt/article/download/159/115), and the
Dorabella study cited on its case page.

## Models and tools installed separately (not in the repository)

| Item | Licence | How |
|---|---|---|
| Tesseract OCR and `tessdata_fast` models | Apache 2.0 | `brew install tesseract`; models: see `data/models/tessdata_fast/MANIFEST.md` after cloning them as described in the README |
| RapidOCR (PaddleOCR detection and recognition models) | Apache 2.0 | `pip install rapidocr-onnxruntime` (in `requirements.txt`) |
| Argos Translate models | Each model's licence in the Argos package index | `scripts/install_translation_models.py`, `scripts/install_more_translators.py` |
| Helsinki-NLP opus-mt-mul-en (Latin drafts) | CC BY 4.0 | downloaded by `scripts/install_translation_models.py` |
| BirdNET 2.4 | CC BY-NC-SA 4.0 (non-commercial) | downloaded on first use |
| YAMNet | Apache 2.0 | downloaded on first use |
| Ollama models (optional, e.g. qwen2.5vl) | Each model's licence | installed by the user with Ollama |
| Python packages | Each package's licence | `requirements.txt` |
| `data/models/objects/` | MobileNetV2 (mobilenetv2-12.onnx, 13.96 MB) and the ImageNet synset list from the ONNX model zoo (github.com/onnx/models), the Lens's classical object fallback; not redistributed | Apache-2.0 |
| `data/lens_debug/objects/` | macOS account pictures converted locally for the object controls; never committed | Apple's images, used locally only |
