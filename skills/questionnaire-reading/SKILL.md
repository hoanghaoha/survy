---
name: questionnaire-reading
description: >
  Use this skill whenever the user wants to read, parse, or understand a questionnaire design
  document (Word .docx, Excel .xlsx, PDF .pdf, or plain text). Triggers include: "read my
  questionnaire", "parse questionnaire design", "extract questions from this file",
  "understand survey structure", "show me the questionnaire layout", "create questionnaire-design.md".
  This skill produces a standardised `questionnaire-design.md` that captures every question's
  ID, label/text, answer options, and routing/skip logic — structured so an AI agent can later
  use it to build or update survy metadata accurately.
---

# Questionnaire Reading Skill

This skill converts a raw questionnaire design document into a structured
`questionnaire-design.md` file. The output becomes the authoritative reference
for survey structure, routing logic, and metadata — enabling an AI agent to
understand the data before writing any survy code.

---

## 1. Input Formats

Accept any of the following:

| Format | How to read |
|--------|-------------|
| `.docx` | Use `python-docx` (`pip install python-docx`) to extract paragraphs and tables |
| `.xlsx` / `.xls` | Use `openpyxl` (`pip install openpyxl`) or `polars.read_excel()` to iterate rows |
| `.pdf` | Use `pdfplumber` (`pip install pdfplumber`) to extract text page by page |
| `.txt` / `.md` | Read directly — plain text, no library needed |

Always inspect the raw content first before deciding on a parsing strategy.
Questionnaire documents vary widely; read several rows/paragraphs to detect
the layout pattern before extracting.

---

## 2. Concepts to Extract

For each question, extract:

| Field | Description |
|-------|-------------|
| **Question ID** | Short code used in data (e.g. `Q1`, `S2`, `D3`). If not present, assign sequentially. |
| **Label / Text** | The full question wording shown to respondents. |
| **Type** | `Single` (one answer), `Multi` (multiple answers), `Open` (free text), `Number`, `Grid`. |
| **Options** | Answer choices with their codes/numbers. Capture exactly as designed. |
| **Logic** | Routing instruction — who sees this question. See Section 3. |
| **Terminate** | Flag if any option ends the interview (`-> Terminate respondent`). |

---

## 3. Logic / Routing Rules

Questionnaire logic is the most important thing to capture accurately.
Common patterns and how to write them in the output:

| Design wording | Output phrasing |
|----------------|-----------------|
| "Ask all" / "All respondents" | `Logic: All respondents` |
| "Ask if Q2 = Yes" / "If Q2 = 1" | `Logic: Ask if Q2 == 1 (Yes)` |
| "Ask if Q3 = 1 or 2" | `Logic: Ask if Q3 == 1 (Cat) OR Q3 == 2 (Dog)` |
| "Skip to Q5 if Q4 = No" | `Logic: Ask if Q4 != 2 (No)` |
| "Ask for all non-terminated" | `Logic: Ask for all respondents (who are not terminated)` |
| "Ask if Q1 is answered" | `Logic: Ask if Q1 is not empty` |
| Grid sub-questions | `Logic: Same as parent grid question` |

When logic is ambiguous, capture the raw wording in a `Note:` line beneath.

---

## 4. Output Format

Always write the output as a `.md` file named `questionnaire-design.md` (or
the name the user specifies). Use this exact structure:

```markdown
# QUESTIONNAIRE DESIGN

---
Question: Q1
Type: Single
Label / Text: Please indicate your gender
Options:
1. Male
2. Female
Logic: All respondents

---
Question: Q2
Type: Single
Label / Text: Do you nurture a pet?
Options:
1. Yes
2. No
Logic: All respondents

---
Question: Q3
Type: Multi
Label / Text: Which type of pet do you nurture?
Options:
1. Cat
2. Dog
3. Other -> Terminate respondent
Logic: Ask if Q2 == 1 (Yes)

---
Question: Q4
Type: Single
Label / Text: Which brand do you choose for pet food?
Options:
1. Brand 1
2. Brand 2
3. Brand 3
Logic: Ask for all respondents (who are not terminated)
```

**Rules for the output:**

- One `---` separator before every question block (including the first).
- `Question:` — use the ID exactly as it appears in the data file (or the questionnaire code).
- `Type:` — one of `Single`, `Multi`, `Open`, `Number`, `Grid`.
- `Label / Text:` — full question wording; do NOT truncate.
- `Options:` — list every answer choice with its numeric code.
  - Append ` -> Terminate respondent` for terminating options.
  - Append ` -> Skip to Q{n}` for options that jump forward.
- `Logic:` — concise routing rule using the patterns in Section 3.
- Add `Note:` only when the original wording is ambiguous or non-standard.
- Omit empty fields (e.g. `Options:` block for Open/Number questions unless codes exist).

---

## 5. Step-by-Step Process

1. **Receive the file path** from the user.
2. **Read the raw content** using the appropriate library (see Section 1).
3. **Identify the layout**: Is it a table? Numbered list? Free-form paragraphs?
4. **Extract each question** in order, filling in every field from Section 2.
5. **Resolve logic**: Map routing instructions to the standard phrasing from Section 3.
6. **Write `questionnaire-design.md`** to the same directory as the input file
   (or to a path the user specifies).
7. **Print a short summary**: total questions found, any questions where logic
   was unclear (flagged with `Note:`).

---

## 6. Parsing Tips by Format

### Word (.docx)
- Questions are usually in tables (one row per question) or numbered paragraphs.
- Use `doc.tables` first; if empty, fall back to `doc.paragraphs`.
- Bold text often marks question IDs or labels.
- Italics or parenthetical text often marks routing instructions.

### Excel (.xlsx)
- Look for a header row containing keywords like "Question", "Code", "Label", "Logic", "Routing".
- Each subsequent row is typically one question or one answer option.
- If rows alternate between question and option levels, detect the pattern by column indentation or a "Type" column value.

### PDF (.pdf)
- Extract text page by page with `pdfplumber`.
- Questionnaires in PDF often use numbering (Q1, Q2, …) as anchors — split on these.
- Tables in PDF may be detected via `page.extract_tables()`.
- Watch for headers/footers repeating on every page — strip them.

### Mixed / Unknown
- If the format is unclear, print the first 20 lines/rows and ask the user to confirm the layout before proceeding.

---

## 7. Example Script

See `scripts/parse_questionnaire.py` for a ready-to-run parser that handles
`.docx`, `.xlsx`, `.pdf`, and `.txt` inputs and writes `questionnaire-design.md`.

---

## 8. Integration with survy

Once `questionnaire-design.md` exists, an AI agent can:

- Read the `Question` IDs and map them to `survey["Q1"]` variable IDs.
- Use `Label / Text` to populate `v.label` via `survey.update(...)`.
- Use `Options` to build correct `value_indices` dicts.
- Use `Logic` to understand which respondents answered each question,
  and apply `survey.filter(...)` correctly in analysis.
- Use `-> Terminate respondent` flags to identify and exclude screened-out rows.

---

## 9. Reference Files

- `scripts/parse_questionnaire.py` — ready-to-run parser for docx/xlsx/pdf/txt
- `assets/sample_questionnaire.docx` — example Word questionnaire design
- `assets/sample_questionnaire_design.md` — expected output for the sample
