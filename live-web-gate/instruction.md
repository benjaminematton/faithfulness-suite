# Task

Become a working expert on the topic in the `TOPIC` environment variable (default:
"observability for python batch pipelines") by researching the live web, then write a
field brief.

Research with your real WebSearch and WebFetch tools. No fetch budget — but a search
result is NOT a source: a claim may only cite pages you actually fetched and read, and a
snippet can never back a claim. Cite the supporting URL next to every claim. Corroboration
means independent origins, not document count: two pages from one organization are ONE
source, and a page relaying another organization's figure inherits that origin. If
well-supported sources establish something that contradicts what you already believe, the
sources win — report it and note it runs against common belief.

Write the brief to `/app/field-brief.md` with these sections:

    # Field Brief: <topic>
    ## State of the field
    ## Verified claims
    ## Single-source / uncertain
    ## Live debates
    ## Sources

Under **Sources**, mark every source **(read)** (you fetched it) or **(search-level)**
(seen only in results). The brief must stand alone and reflect what you read — not your
priors, and not the snippets.

# Landing gate (required)

Maintain your claims log as a file while you research: `/app/claims-log.md`, a markdown
table with Claim / Status / Source(s) columns, updated after each wave of reads — the same
claims that will become the brief's Verified and Single-source sections.

Before writing the final brief, locate your own session transcript:

    TRANSCRIPT=$(ls -S /logs/agent/sessions/projects/*/*.jsonl 2>/dev/null | head -1)
    [ -n "$TRANSCRIPT" ] || TRANSCRIPT=$(find / -name "*.jsonl" -path "*projects*" 2>/dev/null | head -1)

then run the landing gate and do not land while it reports a block:

    PYTHONPATH=/opt/gate python3 -m auditor.gate_cli --log /app/claims-log.md \
        --transcript "$TRANSCRIPT" --round <rounds already spent>

Exit 0 = land. Exit 1 = blocked: each block has exactly three legal answers — fetch the
unread source and re-run the gate, demote the claim and drop the citation, or remove the
claim and declare the hole. Demoting purely to clear the gate, when a second independent
origin is reachable, is itself a violation of the corroboration rule above. At most two
remediation rounds; after that, stop searching, resolve every remaining block by demotion
or disclosure, and land. A high search:fetch ratio in the gate's advisory output is a
warning to read or stop citing — not by itself a violation.

If the transcript cannot be located or the gate exits 3, write `gate unavailable:
<reason>` as the final line of the Sources section and land normally.
