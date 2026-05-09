import importers.common as common


class _MockResponse:
    def __init__(self, text: str):
        self.text = text


class _MockModels:
    def __init__(self, response_text: str):
        self._response_text = response_text
        self.last_prompt = ""

    def generate_content(self, model, contents):
        self.last_prompt = contents
        return _MockResponse(self._response_text)


class _MockLLM:
    def __init__(self, response_text: str = "none"):
        self.models = _MockModels(response_text)


def test_slug_normalization():
    assert common._slug("Nutrien") == "nutrien"
    assert common._slug("Nutrien Ltd.") == "nutrienltd"
    assert common._slug("The Coca-Cola Company") == "thecocacolacompany"
    assert common._slug("Nestlé") == "nestle"
    assert common._slug("") == ""


def test_resolves_exact_slug_match():
    resolver = common.EntityResolver()
    resolver._cache = {
        "nutrien": [common.CachedEntity("c01", "Company", "Nutrien")],
    }
    resolver._loaded = True

    result = resolver.resolve("Nutrien", "company")

    assert result.node_id == "c01"
    assert result.match_status == "matched"
    assert result.matched_via == "slug"


def test_resolves_alias_via_slug():
    resolver = common.EntityResolver()
    resolver._cache = {
        "ntr": [common.CachedEntity("c01", "Company", "Nutrien", aliases=["NTR"])],
    }
    resolver._loaded = True

    result = resolver.resolve("NTR", "company")

    assert result.node_id == "c01"
    assert result.match_status == "matched"


def test_picks_correct_type_when_multiple_slugs_match():
    resolver = common.EntityResolver()
    resolver._cache = {
        "corn": [
            common.CachedEntity("m04", "Commodity", "Corn"),
            common.CachedEntity("c04", "Company", "ADM", aliases=["Corn Processor"]),
        ],
    }
    resolver._loaded = True

    result = resolver.resolve("Corn", "commodity")

    assert result.node_id == "m04"


def test_returns_unmatched_when_no_match_in_cache():
    resolver = common.EntityResolver()
    resolver._cache = {
        "nutrien": [common.CachedEntity("c01", "Company", "Nutrien")],
    }
    resolver._loaded = True

    result = resolver.resolve("TotallyUnknownCorp", "company")

    assert result.node_id is None
    assert result.match_status == "unmatched"


def test_returns_unmatched_when_cache_not_loaded_and_no_session():
    resolver = common.EntityResolver()

    result = resolver.resolve("Nutrien", "company")

    assert result.node_id is None
    assert result.match_status == "unmatched"


def test_llm_fallback_resolves_match():
    resolver = common.EntityResolver(llm_client=_MockLLM(response_text="c01"))
    resolver._cache = {
        "ntr": [common.CachedEntity("c01", "Company", "Nutrien", aliases=["NTR"])],
    }
    resolver._loaded = True

    result = resolver.resolve("Nutrien Ltd.", "company")

    assert result.node_id == "c01"
    assert result.matched_via == "llm"


def test_llm_fallback_returns_none_when_no_match():
    resolver = common.EntityResolver(llm_client=_MockLLM(response_text="none"))
    resolver._cache = {
        "cargill": [common.CachedEntity("c06", "Company", "Cargill")],
    }
    resolver._loaded = True

    result = resolver.resolve("FakeCorp", "company")

    assert result.node_id is None
    assert result.match_status == "unmatched"


def test_slug_removes_accents():
    assert common._slug("Nestlé") == "nestle"
    assert common._slug("São Paulo") == "saopaulo"
    assert common._slug("Cargill") == "cargill"


def test_cache_has_expected_entity():
    resolver = common.EntityResolver()
    resolver._cache = {
        "mosaic": [common.CachedEntity("c03", "Company", "Mosaic")],
        "cargill": [common.CachedEntity("c06", "Company", "Cargill")],
    }
    resolver._loaded = True

    result = resolver.resolve("Mosaic", "company")
    assert result.node_id == "c03"

    result = resolver.resolve("Cargill", "company")
    assert result.node_id == "c06"


def test_stub_creation_via_session():
    resolver = common.EntityResolver()
    resolver._loaded = True

    created_stubs = []

    class MockSession:
        def run(self, query, **params):
            created_stubs.append((query, params))

    result = resolver.resolve("UnknownProductX", "product", session=MockSession())

    assert result.stub_created is True
    assert result.match_status == "unmatched"
    assert result.matched_via == "stub"

    assert len(created_stubs) == 1
    assert "UnknownProductX" in str(created_stubs[0][1])
