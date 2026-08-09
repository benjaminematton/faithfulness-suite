from auditor.urlnorm import normalize_url


def test_default_port_dropped():
    assert normalize_url("https://read.example.com:443/p") == \
        normalize_url("https://read.example.com/p") == "read.example.com/p"


def test_userinfo_stripped():
    assert normalize_url("https://u:p@host.com/x") == normalize_url("https://host.com/x") == \
        "host.com/x"


def test_tracking_params_stripped_others_kept():
    assert normalize_url("https://a.com/p?utm_source=x&id=2") == \
        normalize_url("https://a.com/p?id=2") == "a.com/p?id=2"


def test_nondefault_port_kept():
    assert normalize_url("https://a.com:8080/p") == "a.com:8080/p"


def test_malformed_port_does_not_raise():
    # non-numeric port suffix — urlparse's .port raises ValueError; must not propagate.
    # hostname still parses cleanly; the malformed port is dropped, not appended.
    assert normalize_url("https://read.example.com:80x/p") == "read.example.com/p"


def test_ref_param_is_preserved():
    assert normalize_url("https://a.com/p?ref=main") == "a.com/p?ref=main"
