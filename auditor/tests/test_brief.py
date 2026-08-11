# auditor/tests/test_brief.py
from auditor.brief import parse_brief, resolve_citations

TABLE_BRIEF = """# Field brief: X
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| gBETA is a 7-week pre-accelerator | verified | [g](https://www.gener8tor.com/gbeta), [g2](https://www.gener8tor.com/gbeta/medtech) |
| Cohorts end in graduation | verified | [h](https://journals.uchicago.edu/doi/full/10.1086/684985) |
| Alumni anchor at first entry | single-source | [s](https://sopact.com/use-case) |
## Source shelf
- [g](https://www.gener8tor.com/gbeta) — vendor **(read)**
- [h](https://journals.uchicago.edu/doi/full/10.1086/684985) — journal **(search-level)**
"""

SECTION_BRIEF = """# Field Brief: Y
## Verified claims
- RDHx rejects more heat (doc_a, doc_b). See [c](https://a.example.com/r).
## Single-source / uncertain
- Pressure testing dominates ([p](https://ops.example.org/post)).
"""


def test_table_brief_claims_and_statuses():
    b = parse_brief(TABLE_BRIEF)
    ver = [c for c in b.claims if c.status == "verified"]
    assert len(ver) == 2
    assert "gener8tor.com/gbeta" in ver[0].cited_urls
    assert "gener8tor.com/gbeta/medtech" in ver[0].cited_urls
    single = [c for c in b.claims if c.status == "single-source"]
    assert len(single) == 1


def test_shelf_marks_parsed():
    b = parse_brief(TABLE_BRIEF)
    marks = {url: mark for url, mark, _title in b.shelf}
    assert marks["gener8tor.com/gbeta"] == "read"
    assert marks["journals.uchicago.edu/doi/full/10.1086/684985"] == "search-level"


def test_shelf_entries_carry_titles():
    b = parse_brief(TABLE_BRIEF)
    titles = {url: title for url, _mark, title in b.shelf}
    assert titles["gener8tor.com/gbeta"] == "g"
    assert titles["journals.uchicago.edu/doi/full/10.1086/684985"] == "h"


def test_section_brief_maps_section_to_status():
    b = parse_brief(SECTION_BRIEF)
    ver = [c for c in b.claims if c.status == "verified"]
    assert len(ver) == 1
    assert ver[0].cited_urls == ["a.example.com/r"]
    assert ver[0].doc_refs == ["doc_a", "doc_b"]
    assert [c for c in b.claims if c.status == "single-source"]


def test_brief_without_claims_yields_empty():
    b = parse_brief("# hi\nno structure here")
    assert b.claims == []


def test_negated_statuses_do_not_match():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x | unverified | [a](https://a.com/1) |
| y | uncontested | [b](https://b.com/2) |
"""
    assert parse_brief(md).claims == []


def test_exact_statuses_still_match():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x | verified | [a](https://a.com/1) |
| y | single-source | [b](https://b.com/2) |
"""
    statuses = [c.status for c in parse_brief(md).claims]
    assert statuses == ["verified", "single-source"]


def test_decorated_status_cells_parse():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x | verified ✅ | [a](https://a.com/1) |
| y | Verified (2 sources) | [b](https://b.com/2) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 2
    assert all(c.status == "verified" for c in b.claims)
    assert b.dropped_rows == 0


def test_stray_table_does_not_suppress_section_pass():
    md = """# B

| Name | Role | Notes |
|---|---|---|
| Ada | Eng | n/a |

## Verified claims
- Something true happens here (doc_a).
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert b.claims[0].status == "verified"


def test_unrecognized_status_row_counts_as_dropped():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x | questionable | [a](https://a.com/1) |
"""
    b = parse_brief(md)
    assert b.claims == []
    assert b.dropped_rows == 1


def test_nested_bullet_absorbed_into_parent_not_separate_claim():
    md = """# B
## Verified claims
- Top-level claim here (doc_a).
  - Nested detail that should not become its own claim.
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert "Top-level" in b.claims[0].text
    assert "Nested detail" in b.claims[0].text


def test_horizontal_rule_produces_no_claim():
    md = """# B
## Verified claims
---
- Real claim goes here (doc_a).
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert "Real claim" in b.claims[0].text


def test_no_space_heading_ends_section():
    md = """# B
## Verified claims
- Real claim goes here (doc_a).
##Notes
- This should not be captured as a verified claim.
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert "Real claim" in b.claims[0].text


def test_four_column_table_status_in_column_1():
    md = """# B
## Key claims log
| Claim | Status | Source(s) | Notes |
|---|---|---|---|
| x is true | Verified (2 sources) | [a](https://a.com/1) | fine |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    c = b.claims[0]
    assert c.status == "verified"
    assert c.cited_urls == ["a.com/1"]
    assert "x is true" in c.text


def test_five_column_table_status_in_column_2():
    md = """# B
## Key claims log
| Claim | Evidence | Status | Source(s) | Notes |
|---|---|---|---|---|
| x is true | strong | verified | [a](https://a.com/1) | fine |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    c = b.claims[0]
    assert c.status == "verified"
    assert c.cited_urls == ["a.com/1"]
    assert c.text.startswith("x is true")


def test_verification_status_header_wording_starts_claims_table():
    md = """# B
## Key claims log
| Claim | Verification status | Source(s) |
|---|---|---|
| x is true | verified | [a](https://a.com/1) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert b.claims[0].status == "verified"


def test_all_rows_unrecognized_status_all_dropped():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x | questionable | [a](https://a.com/1) |
| y | maybe | [b](https://b.com/2) |
| z | tbd | [c](https://c.com/3) |
"""
    b = parse_brief(md)
    assert b.claims == []
    assert b.dropped_rows == 3


def test_data_row_with_status_word_in_claim_text_is_not_eaten_as_header():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| The scheduler exposes a job status endpoint | verified | [z](https://never-fetched.example.org/z9) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    c = b.claims[0]
    assert c.status == "verified"
    assert "job status endpoint" in c.text
    assert c.cited_urls == ["never-fetched.example.org/z9"]
    assert b.dropped_rows == 0


def test_reordered_header_status_and_sources_columns():
    md = """# B
## Key claims log
| Claim | Source(s) | Status |
|---|---|---|
| x is true | [a](https://a.com/1) | verified |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    c = b.claims[0]
    assert c.status == "verified"
    assert c.cited_urls == ["a.com/1"]
    assert "x is true" in c.text


def test_leading_index_column_claim_text_from_claim_column():
    md = """# B
## Key claims log
| # | Claim | Status | Source(s) |
|---|---|---|---|
| 1 | The widget ships in Q3 | verified | [a](https://a.com/1) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    c = b.claims[0]
    assert c.status == "verified"
    assert not c.text[:1].isdigit()
    assert c.text.startswith("The widget ships in Q3")


def test_status_table_without_claim_header_is_stray_and_section_still_parsed():
    md = """# B
## Legend
| Source | Status | Notes |
|---|---|---|
| a.com | verified | fine |
| b.com | contested | debated |

## Verified claims
- Something true happens here (doc_a).
"""
    b = parse_brief(md)
    assert len(b.claims) == 1
    assert b.claims[0].status == "verified"
    assert "Something true" in b.claims[0].text
    assert b.dropped_rows == 0


def test_plural_claims_header_recognized():
    md = """# B
## Key claims log
| Claims | Status | Source(s) |
|---|---|---|
| x is true | verified | [a](https://a.com/1) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1 and b.claims[0].status == "verified"


def test_status_vocab_in_header_cells_ok():
    md = """# B
| Claim | Status | Source(s) | Single-source risk |
|---|---|---|---|
| x is true | verified | [a](https://a.com/1) | low |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1 and "a.com/1" in b.claims[0].cited_urls


def test_search_level_status_recognized():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x might be true | search-level only | [a](https://a.com/1) |
"""
    b = parse_brief(md)
    assert len(b.claims) == 1 and b.claims[0].status == "search-level"
    assert b.dropped_rows == 0


def test_multiline_bullet_absorbs_continuation_citations():
    md = """# B
## Verified claims
- **OTel is the standard.** Used by Elastic
  and OneUptime.
  ([Elastic](https://elastic.co/blog/x),
  [OneUptime](https://oneuptime.com/blog/y))
- Second claim ([z](https://z.example.com/p)).
## Single-source / uncertain
- One source thing ([s](https://s.example.org/q)).
"""
    b = parse_brief(md)
    ver = [c for c in b.claims if c.status == "verified"]
    assert len(ver) == 2
    assert set(ver[0].cited_urls) == {"elastic.co/blog/x", "oneuptime.com/blog/y"}
    assert ver[1].cited_urls == ["z.example.com/p"]


def test_nested_bullet_urls_attach_to_parent_not_separate_claim():
    md = """# B
## Verified claims
- Parent claim, two ways:
  - *first way* ([a](https://a.example.com/1))
  - *second way* ([b](https://b.example.org/2))
"""
    b = parse_brief(md)
    ver = [c for c in b.claims if c.status == "verified"]
    assert len(ver) == 1
    assert set(ver[0].cited_urls) == {"a.example.com/1", "b.example.org/2"}


NAME_CITED_BRIEF = """# B
## Verified claims
- Core outcome indicators are harmonized, per GALI Acceleration Report and Kauffman Measurement Brief.
- Something entirely unrelated to any source.
## Source shelf
- [GALI Acceleration Report](https://galidata.org/r1) — **(read)**
- [Kauffman Measurement Brief](https://kauffman.org/b2) — **(read)**
"""


def test_name_cited_claim_resolves_via_shelf():
    b = parse_brief(NAME_CITED_BRIEF)
    resolve_citations(b)
    named = next(c for c in b.claims if c.text.startswith("Core outcome"))
    assert set(named.cited_urls) == {"galidata.org/r1", "kauffman.org/b2"}
    assert named.resolved_via_shelf is True


def test_non_matching_claim_stays_unresolved():
    b = parse_brief(NAME_CITED_BRIEF)
    resolve_citations(b)
    unrelated = next(c for c in b.claims if c.text.startswith("Something entirely"))
    assert unrelated.cited_urls == []
    assert unrelated.resolved_via_shelf is False


def test_resolve_citations_leaves_already_cited_claims_untouched():
    b = parse_brief(TABLE_BRIEF)
    before = [list(c.cited_urls) for c in b.claims]
    resolve_citations(b)
    after = [list(c.cited_urls) for c in b.claims]
    assert before == after
    assert all(not c.resolved_via_shelf for c in b.claims)


def test_resolution_uses_full_text_beyond_display_truncation():
    filler = "word " * 70  # pushes citation past the 300-char display cap
    md = f"""# B
## Verified claims
- Claim body {filler} per GALI Does Acceleration Work and the Hochberg Seed Accelerator Model report.
## Sources
- [GALI — Does Acceleration Work? Five Years of Evidence](https://galidata.org/daw) — **(read)**
- [Hochberg — Accelerating Entrepreneurs and Ecosystems: The Seed Accelerator Model](https://example.edu/ham) — **(read)**
- [GALI — A Rocket or a Runway? Venture Growth during Acceleration](https://galidata.org/rocket) — **(read)**
"""
    from auditor.brief import parse_brief, resolve_citations
    b = parse_brief(md)
    resolve_citations(b)
    ver = [c for c in b.claims if c.status == "verified"][0]
    assert "galidata.org/daw" in ver.cited_urls
    assert "example.edu/ham" in ver.cited_urls
    assert "galidata.org/rocket" not in ver.cited_urls  # named neither Rocket nor Runway


def test_disclosed_search_level_url_excluded_from_cited_urls():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x is true | verified | [Verified Misguidance](https://a.com/x); [CiteEval](https://b.com/y); (search-level: [ALiiCE](https://c.com/z)) |
"""
    b = parse_brief(md)
    c = b.claims[0]
    assert "c.com/z" not in c.cited_urls
    assert set(c.cited_urls) == {"a.com/x", "b.com/y"}
    assert c.disclosed_search_level == ["c.com/z"]


def test_disclosed_search_level_nested_parens_both_excised():
    md = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| x is true | verified | (search-level: [A](https://a.com/1), [B](https://b.com/2)) |
"""
    b = parse_brief(md)
    c = b.claims[0]
    assert c.cited_urls == []
    assert set(c.disclosed_search_level) == {"a.com/1", "b.com/2"}


def test_qualified_shelf_marks_parse():
    md = """# B
## Sources
- [GALI — Does Acceleration Work?](https://galidata.org/daw.pdf) — **(read, pp.4–11)** canonical synthesis
- [Seitz meta-analysis](https://repec.org/seitz) — **(read, abstract only)** full text unreachable
- [ANDE hub](https://andeglobal.org/hub) — (search-level, seen in results)
"""
    b = parse_brief(md)
    marks = {url: mark for url, mark, _t in b.shelf}
    assert marks["galidata.org/daw.pdf"] == "read"
    assert marks["repec.org/seitz"] == "read"
    assert marks["andeglobal.org/hub"] == "search-level"
