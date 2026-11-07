# Lab Report Summarizer

An offline pipeline that reads lab reports (digital PDFs, scans and phone photos), extracts test values with OCR, flags Low/High results in code, warns about doubtful readings, and writes a plain-language summary with a local LLM. All processing runs on the user's machine.

> ⚠️ **Not medical advice.** This tool explains lab values and does not diagnose. Always check the extracted values against the original report and consult a doctor. It is a research and learning project, not a medical device.

## Design principles

1. **Code decides facts, AI only reads and rewords.** Low/High/Normal is computed by arithmetic, never by the LLM.
2. **Flag, never silently correct.** Suspicious values (lost decimals, dropped digits) are shown with a reason, a suggestion and a second OCR reading.
3. **Human confirms.** Flagged rows must be confirmed or fixed before a summary is written.
4. **Private by design.** No cloud services, no accounts, no data upload.

## Pipeline

```
Upload → Ingest → Preprocess → OCR (2 passes) → Parse → Analyze → Quality checks → Human review → Summary
```

| Stage | Technology |
|---|---|
| PDF reading | PyMuPDF (text layer and word coordinates) |
| Image cleanup | OpenCV: lighting normalization, projection-profile deskew, table-line removal |
| OCR | Tesseract 5 (LSTM) |
| Parsing and checks | Rule-based Python: regex, 10 quality checks |
| Summary | Local LLM via Ollama (Llama 3.2 3B) |
| Interface | Streamlit |
| Tests | pytest |

Digital PDFs skip OCR. Images are read twice (`basic` primary, `full` second opinion) and disagreements are flagged.

## Setup

**Requirements:** Python 3.10+ (3.12 recommended), [Tesseract 5](https://github.com/UB-Mannheim/tesseract/wiki), [Ollama](https://ollama.com) with `ollama pull llama3.2:3b`.

```bash
git clone https://github.com/<user>/lab-report-summarizer.git
cd lab-report-summarizer
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python check_setup.py          # all lines should say [ OK ]
```

On Windows, if Tesseract is not at `C:\Program Files\Tesseract-OCR`, edit `TESSERACT_CMD` in `config.py`.

## Run

```bash
ollama serve                   # skip if it already runs as a service
streamlit run app.py           # opens http://localhost:8501
```

If Ollama is off, the app still works and uses a rule-based summary.

## Data

**No real reports are included**, and `data/` is git-ignored. Generate synthetic test data:

```bash
python generate_samples.py     # synthetic reports + answer keys in data/samples/
```

To evaluate on your own reports, put de-identified files in `data/samples/real/`, create answer keys with `python make_key_template.py <file>` (then correct every row **from the image**), and run:

```bash
python evaluate.py synth --n 6
python evaluate.py real
```

Never commit real patient reports, even redacted ones.

## Tests

```bash
python -m pytest tests -q
```

## Results (v1 baseline)

Measured on **10 real reports used during development (dev set, so figures are optimistic)**, 116 hand-labelled rows:

| Metric | Result |
|---|---|
| Rows found (extraction recall) | 85.3% (99/116) |
| Rows fully correct (value and range) | 62.9% (73/116) |
| Wrong rows that carried a ⚠️ | 78.1% (25/32) |
| Silent errors (wrong and unflagged) | 6.7% (7/105) |
| Wrong Low/High/Normal status, unflagged | 0 of 105 |
| Review burden | 31.4% |

Ablation: image preprocessing raised row accuracy from 25.0% to 62.9%. A second OCR pass raised flag recall from 65.6% to 78.1% at the cost of more false alarms.

Held-out evaluation is the next milestone.

## Project structure

```
├── app.py                 Streamlit app
├── config.py              Paths and settings
├── check_setup.py         Installation check
├── generate_samples.py    Synthetic report generator
├── make_scans.py          Simulated scan PDFs
├── make_key_template.py   Answer-key template
├── evaluate.py            Metrics and ablations
├── test_ocr.py            OCR benchmark
├── run_parser.py          Parse real files from the command line
├── src/
│   ├── ingest.py          PDF/image loading, row rebuilding
│   ├── preprocess.py      Image cleanup
│   ├── ocr.py             Tesseract wrapper
│   ├── parser.py          Row extraction
│   ├── analyzer.py        Low/High/Normal
│   ├── checks.py          Differential-count check
│   ├── quality.py         Two-pass disagreement, warnings
│   └── summarizer.py      LLM summary with fallback
└── tests/                 pytest cases
```

## Known limitations

- Rules were tuned on the 10 development reports. Unseen lab layouts may need new patterns.
- 17 of 116 rows were missed, and 7 wrong rows were unflagged.
- Qualitative (urine) rows are displayed but are not yet editable or evaluated.
- Summary quality is not yet evaluated, and the LLM output is not verified.
- Cut-off or very blurry photos cannot be recovered. The app asks for a better photo.

## Roadmap

- [ ] Held-out evaluation and diagnosis of missed rows
- [ ] Correction log and labelling tool
- [ ] Second OCR engine with voting
- [ ] ClinicalBERT test-name normalization (compared against a dictionary baseline)
- [ ] Learned model that predicts misread rows
- [ ] LLM number-faithfulness check
- [ ] FastAPI backend, Docker, CI

## Team

| Name | Area |
|---|---|
| [Name] | Parser, quality checks, evaluation |
| [Name] | Vision and OCR |
| [Name] | NLP and ClinicalBERT |

## Licence and third-party notes

Licence: [to be decided by the team]. PyMuPDF is AGPL-licensed, and the Llama and ClinicalBERT models have their own licence terms. Check them before any public or commercial use.
