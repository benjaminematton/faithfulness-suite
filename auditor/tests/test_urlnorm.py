from auditor.urlnorm import normalize_url, registered_domain


def test_normalize_strips_scheme_www_slash_fragment():
    assert normalize_url("https://www.gener8tor.com/gbeta/") == "gener8tor.com/gbeta"
    assert normalize_url("http://gener8tor.com/gbeta#top") == "gener8tor.com/gbeta"
    assert normalize_url("https://docs.python.org/3/library/logging.html?x=1") == \
        "docs.python.org/3/library/logging.html?x=1"


def test_normalize_is_idempotent_and_handles_bare_host():
    assert normalize_url("Example.COM") == "example.com"
    assert normalize_url(normalize_url("https://www.example.com/a/")) == "example.com/a"


def test_registered_domain_groups_subdomains():
    assert registered_domain("docs.python.org/x") == "python.org"
    assert registered_domain("gener8tor.com/gbeta") == "gener8tor.com"
    assert registered_domain("blog.imranghory.org/post") == "imranghory.org"
