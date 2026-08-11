"""URL identity for the auditor. All comparisons between cited and fetched URLs go
through normalize_url; origin grouping goes through registered_domain (a last-two-labels
heuristic — good enough for D3 flags, which the judge confirms or dismisses)."""

from urllib.parse import urlparse, parse_qsl, urlencode

_TRACKING_EXACT = {"fbclid", "gclid"}


def _strip_tracking(query: str) -> str:
    if not query:
        return ""
    kept = [
        (k, v) for k, v in parse_qsl(query, keep_blank_values=True)
        if not k.startswith("utm_") and k not in _TRACKING_EXACT
    ]
    return urlencode(kept)


def normalize_url(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    try:
        port = p.port
    except ValueError:
        port = None
    if port is not None and port not in (80, 443):
        host += f":{port}"
    path = p.path.rstrip("/")
    out = host + path
    query = _strip_tracking(p.query)
    if query:
        out += "?" + query
    return out


def registered_domain(norm_url: str) -> str:
    host = norm_url.split("/")[0].split("?")[0]
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


MULTI_TENANT_HOSTS = {
    "arxiv.org", "biorxiv.org", "ssrn.com", "osf.io", "zenodo.org",
    "github.com", "gitlab.com", "medium.com", "huggingface.co",
}


def origin_key(norm_url: str) -> str:
    """Origin identity for D3 clustering. For multi-tenant repository hosts,
    two documents are NOT one origin just because they share the host --
    distinguish by first path segment where meaningful (github.com/user),
    else treat each document as its own origin (arxiv.org papers)."""
    dom = registered_domain(norm_url)
    if dom not in MULTI_TENANT_HOSTS:
        return dom
    parts = norm_url.split("?")[0].split("/")
    if dom in ("github.com", "gitlab.com", "medium.com", "huggingface.co") and len(parts) > 1 and parts[1]:
        return f"{dom}/{parts[1]}"
    return norm_url  # each repository document is its own origin
