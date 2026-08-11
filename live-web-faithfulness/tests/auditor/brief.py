"""Parse a field brief into claims with statuses and citations.

Two shapes supported (both observed in real briefs during the 2026-08-09 mining pass):
1) a claims-log markdown table with an explicit Status column;
2) status-by-section briefs ("## Verified claims" etc.).
A brief with neither yields zero claims — the audit reports "nothing to audit" rather
than erroring (design: tolerant of format drift)."""

import re
from dataclasses import dataclass, field

from .urlnorm import normalize_url

STATUSES = ("verified", "single-source", "contested", "inference", "prior-knowledge", "search-level")
_URL = re.compile(r"\((https?://[^)\s]+)\)")
_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
_DOC = re.compile(r"\bdoc_[a-z]\b")
_SHELF_MARK = re.compile(r"\((read|search-level)\b[^)]*\)", re.I)
_SEP_CELL = re.compile(r"^:?-+:?$")
_HRULE = re.compile(r"^\s*[-*_]{2,}\s*$")
_TOP_BULLET = re.compile(r"^(?:[-*]\s|\d+[.)]\s)")
_STATUS_RE = {
    s: re.compile(rf"(?<![\w-]){re.escape(s)}(?![\w-])") for s in STATUSES
}
_CLAIM_WORD = re.compile(r"\bclaims?\b")
_STATUS_WORD = re.compile(r"\bstatus\b")
_SRC_WORD = re.compile(r"\b(source|sources|citation|citations|link|links|url|urls)\b")

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "and", "for", "with", "from", "a", "an", "of", "in", "on", "to",
    "at", "by", "or", "vs",
}


def _tokenize(text):
    """Lowercase alphanumeric words >=3 chars, minus a small stopword list."""
    return {w for w in _WORD.findall(text.lower()) if len(w) >= 3 and w not in _STOPWORDS}

_SECTION_STATUS = [
    ("verified claims", "verified"),
    ("single-source", "single-source"),
    ("live debates", "contested"),
]


@dataclass
class Claim:
    text: str
    status: str
    cited_urls: list = field(default_factory=list)
    doc_refs: list = field(default_factory=list)
    resolved_via_shelf: bool = False
    full_text: str = ""
    disclosed_search_level: list = field(default_factory=list)


@dataclass
class Brief:
    claims: list = field(default_factory=list)
    shelf: list = field(default_factory=list)  # (normalized url, mark, title)
    dropped_rows: int = 0


def _clean_heading(line):
    return re.sub(r"[*_`]", "", line.lstrip("#")).strip().lower()


def _clean_cell(cell):
    return re.sub(r"[*_`]", "", cell).strip().lower()


def _match_status(cell):
    cleaned = _clean_cell(cell)
    for s in STATUSES:
        if _STATUS_RE[s].search(cleaned):
            return s
    return None


def _row_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator_row(cells):
    return bool(cells) and all(_SEP_CELL.match(c) for c in cells)


def _excise_search_level(text):
    """Remove '(search-level ...)' disclosure parentheticals from text, returning
    (remainder, excised_spans). Disclosures are inline transparency notes such as
    '(search-level: [ALiiCE](https://...))' -- the whole parenthetical, including any
    nested markdown-link parens, is found by scanning forward from '(search-level'
    with a paren-depth counter to the matching close. Excised spans are returned
    separately so their URLs can be recorded (but never treated as citations)."""
    out = []
    excised = []
    i = 0
    n = len(text)
    lower = text.lower()
    while i < n:
        idx = lower.find("(search-level", i)
        if idx == -1:
            out.append(text[i:])
            break
        out.append(text[i:idx])
        depth = 0
        j = idx
        while j < n:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        excised.append(text[idx:j])
        i = j
    return "".join(out), excised


def _claim_from_text(text, status):
    cleaned = re.sub(r"\s+", " ", text).strip()
    remainder, excised_spans = _excise_search_level(text)
    disclosed = [normalize_url(u) for span in excised_spans for u in _URL.findall(span)]
    return Claim(
        text=cleaned[:300],
        status=status,
        cited_urls=[normalize_url(u) for u in _URL.findall(remainder)],
        doc_refs=sorted(set(_DOC.findall(text))),
        full_text=cleaned,
        disclosed_search_level=disclosed,
    )


def parse_brief(md: str) -> Brief:
    b = Brief()
    lines = md.splitlines()

    # Pass 1: claims-log table rows, keyed on the table HEADER: a row can only
    # START a claims table (the header probe never re-fires on rows already
    # inside one — data rows are never re-probed). A row is a header iff SOME
    # cell contains the word-bounded token "claim" AND some (other) cell
    # contains the word-bounded token "status", AND no cell in the row matches
    # a known status VALUE (verified/single-source/...) — that last guard stops
    # a data row like "| ... a job status endpoint | verified | ... |" from
    # ever being mistaken for a header. claim_idx/status_idx are the indices of
    # the matching cells; src_idx is the first cell mentioning
    # source/sources/citation(s)/link(s)/url(s), else status_idx + 1 when that
    # column exists in the header row, else None. Tables whose header has
    # "status" wording but no "claim" wording (Source/Status/Notes shelves,
    # Component/Status legends, ...) are ordinary stray tables: fully ignored,
    # no dropped_rows, no suppression of the Pass 2 section scan.
    saw_claims_table = False
    in_claims_table = False
    status_idx = claim_idx = src_idx = None
    for line in lines:
        if not line.strip().startswith("|"):
            in_claims_table = False
            status_idx = claim_idx = src_idx = None
            continue
        cells = _row_cells(line)
        if _is_separator_row(cells):
            continue  # separator rows never change table state
        if not in_claims_table:
            cleaned = [_clean_cell(c) for c in cells]
            claim_i = next((i for i, c in enumerate(cleaned) if _CLAIM_WORD.search(c)), None)
            status_i = next((i for i, c in enumerate(cleaned) if _STATUS_WORD.search(c)), None)
            if claim_i is not None and status_i is not None and claim_i != status_i:
                in_claims_table = True
                saw_claims_table = True
                claim_idx = claim_i
                status_idx = status_i
                src_i = next((i for i, c in enumerate(cleaned) if _SRC_WORD.search(c)), None)
                if src_i is None:
                    src_i = status_i + 1 if status_i + 1 < len(cells) else None
                src_idx = src_i
            # header row (or a non-header row of a stray/unstarted table) is
            # never a data row
            continue
        if len(cells) <= max(claim_idx, status_idx):
            b.dropped_rows += 1
            continue
        status = _match_status(cells[status_idx])
        if status:
            text = cells[claim_idx]
            if src_idx is not None and src_idx < len(cells):
                text = text + " " + cells[src_idx]
            b.claims.append(_claim_from_text(text, status))
        else:
            b.dropped_rows += 1

    # Pass 2: status-by-section bullets (only if no claims table was seen)
    #
    # A top-level bullet (indent 0) starts a claim; every subsequent line is
    # absorbed into that SAME claim's text until the next top-level bullet, a
    # heading (any "#" line, any level), a horizontal rule, or end of input.
    # Absorbed lines include indented continuation prose and indented nested
    # bullets — their text and URLs attach to the parent claim rather than
    # becoming claims of their own — plus blank lines (a blank line does not
    # end the claim; only the terminators above do). This lets multi-line
    # bullets whose citations sit on a continuation/nested line still surface
    # their cited_urls instead of coming back "unsupported (no citation)".
    if not saw_claims_table:
        current = None
        n = len(lines)
        i = 0
        while i < n:
            line = lines[i]
            if _HRULE.match(line):
                i += 1
                continue  # horizontal rules are never claims (checked before bullets)
            stripped = line.strip()
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                if level <= 2:
                    h = _clean_heading(line)
                    current = next((s for k, s in _SECTION_STATUS if h.startswith(k)), None)
                # level >= 3 sub-headings do not reset current section status
                i += 1
                continue
            if current and _TOP_BULLET.match(line):
                first = re.sub(r"^[-*]\s?|^\d+[.)]\s", "", line)
                absorbed = [first]
                j = i + 1
                while j < n:
                    nxt = lines[j]
                    if _HRULE.match(nxt) or nxt.strip().startswith("#") or _TOP_BULLET.match(nxt):
                        break
                    absorbed.append(nxt)
                    j += 1
                text = "\n".join(absorbed)
                if sum(ch.isalpha() for ch in text) >= 3:
                    b.claims.append(_claim_from_text(text, current))
                i = j
                continue
            i += 1

    # Pass 3: source shelf marks (works in both shapes)
    in_shelf = False
    for line in lines:
        if line.strip().startswith("#"):
            in_shelf = _clean_heading(line).startswith(("source shelf", "sources"))
        elif in_shelf:
            mark = _SHELF_MARK.search(line)
            if not mark:
                continue
            links = _LINK.findall(line)
            if links:
                title, url = links[0]
            else:
                urls = _URL.findall(line)
                if not urls:
                    continue
                title, url = "", urls[0]
            b.shelf.append((normalize_url(url), mark.group(1).lower(), title.strip()))
    return b


def resolve_citations(brief: Brief) -> None:
    """For claims with no cited_urls, try to resolve citations by NAME against
    the source shelf's titles. Conservative and deterministic: a shelf entry
    matches a claim only when at least 2 of its distinctive title tokens
    appear in the claim text AND at least half of its distinctive title
    tokens appear. Every matching entry's URL is attached (ambiguity is fine
    -- citing two named sources means both are cited). Claims that already
    have cited_urls, or that match nothing on the shelf, are left untouched."""
    for c in brief.claims:
        if c.cited_urls:
            continue
        claim_tokens = _tokenize(c.full_text or c.text)
        if not claim_tokens:
            continue
        matched_urls = []
        for url, _mark, title in brief.shelf:
            title_tokens = _tokenize(title)
            if not title_tokens:
                continue
            overlap = title_tokens & claim_tokens
            if len(overlap) >= 2 and 2 * len(overlap) >= len(title_tokens):
                if url not in matched_urls:
                    matched_urls.append(url)
        if matched_urls:
            c.cited_urls = matched_urls
            c.resolved_via_shelf = True
