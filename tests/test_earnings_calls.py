import json

from importers.earnings_calls import (
    EarningsCallImporter,
    RELATION_TYPE_MAP,
    CONFIDENCE_MAP,
    _build_source,
    _extract_quarter,
)


def _make_relation(overrides: dict = None) -> dict:
    base = {
        "relation_id": "TST--relation--0001",
        "transcript_id": "TST-2025Q1",
        "relation_type": ":PROVIDES",
        "subject_entity": {"name": "Nutrien", "type": "company"},
        "match_status_subject": "unmatched",
        "object_entity": {"name": "Potash", "type": "commodity"},
        "match_status_object": "unmatched",
        "statement": "Nutrien provides potash.",
        "llm_confidence": "explicit",
        "evidence_quality": "explicit",
        "valid_from": None,
        "valid_until": None,
        "is_termination": False,
        "temporal": {"granularity": "ongoing", "start": None, "end": None, "duration": None},
        "source": {"section": "prepared_remarks", "speaker": "CEO", "excerpt": "Nutrien provides potash."},
    }
    if overrides:
        base.update(overrides)
    return base


class _MockResolutionResult:
    def __init__(self, node_id="c01", match_status="matched", node_label="Company", stub_created=False):
        self.node_id = node_id
        self.match_status = match_status
        self.node_label = node_label
        self.stub_created = stub_created


class _MockResolver:
    def __init__(self):
        self.resolve_calls = []
        self._results = {
            ("Nutrien", "company"): _MockResolutionResult("c01", "matched", "Company"),
            ("Potash", "commodity"): _MockResolutionResult("m01", "matched", "Commodity"),
            ("Cargill", "company"): _MockResolutionResult("c06", "matched", "Company"),
        }

    def load_cache(self, session):
        pass

    def resolve(self, name, entity_type, session=None):
        self.resolve_calls.append((name, entity_type))
        return self._results.get(
            (name, entity_type),
            _MockResolutionResult(None, "unmatched", None),
        )


class _Result:
    def __init__(self, records):
        self._records = records

    def single(self):
        return self._records[0] if self._records else None


class _Record:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _MockSession:
    def __init__(self):
        self.commands = []
        self._existing = {}

    def set_existing(self, from_id, to_id, confidence="associated", valid_until=None):
        self._existing[(from_id, to_id)] = {
            "confidence": confidence,
            "valid_until": valid_until,
        }

    def run(self, query, **params):
        self.commands.append((query[:80], params))

        for (f, t), data in self._existing.items():
            if f == params.get("from_id") and t == params.get("to_id"):
                return _Result([_Record(data)])

        return _Result([])


class TestBuildSource:
    def test_builds_structured_source_string(self):
        rel = _make_relation()
        result = _build_source(rel)
        assert result.startswith("transcript:TST-2025Q1|speaker:CEO|excerpt:")
        assert "Nutrien provides potash" in result

    def test_handles_missing_speaker(self):
        rel = _make_relation({"source": {"section": "prepared_remarks", "speaker": None, "excerpt": "test"}})
        result = _build_source(rel)
        assert "speaker:unknown" in result


class TestExtractQuarter:
    def test_extracts_quarter_from_filename(self):
        assert _extract_quarter("data/relations_2025Q1.jsonl") == "2025Q1"
        assert _extract_quarter("relations_2025Q3.jsonl") == "2025Q3"

    def test_raises_on_bad_path(self):
        try:
            _extract_quarter("bad_file.jsonl")
            assert False, "should have raised"
        except ValueError:
            pass


class TestEarningsCallImporter:
    def test_processes_provide_relation_with_explicit_confidence(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({"relation_type": ":PROVIDES", "evidence_quality": "explicit"})

        importer._process_relation(session, rel, "2025Q1")

        assert len(session.commands) >= 1
        cmd, params = session.commands[-1]
        assert params["confidence"] == "confirmed"
        assert params["needs_review"] is False

    def test_supplies_to_without_dates_gets_associated_and_flagged(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({
            "relation_type": ":SUPPLIES_TO",
            "evidence_quality": "explicit",
            "subject_entity": {"name": "Nutrien", "type": "company"},
            "object_entity": {"name": "Cargill", "type": "company"},
        })

        importer._process_relation(session, rel, "2025Q1")

        cmd, params = session.commands[-1]
        assert params["confidence"] == "associated"
        assert params["needs_review"] is True

    def test_skips_division_entity(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({"subject_entity": {"name": "Corn Division", "type": "division"}})

        importer._process_relation(session, rel, "2025Q1")

        assert importer.stats["skipped_division"] == 1

    def test_skips_termination(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({"is_termination": True})

        importer._process_relation(session, rel, "2025Q1")

        assert importer.stats["skipped_termination"] == 1

    def test_service_mapped_to_product(self):
        resolver = _MockResolver()
        resolver._results[("Logistics Service", "service")] = _MockResolutionResult("p14", "matched", "Product")
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({
            "relation_type": ":PROVIDES",
            "subject_entity": {"name": "Nutrien", "type": "company"},
            "object_entity": {"name": "Logistics Service", "type": "service"},
        })

        importer._process_relation(session, rel, "2025Q1")

        assert len(session.commands) >= 1

    def test_used_in_has_no_confidence(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({"relation_type": ":USED_IN"})

        importer._process_relation(session, rel, "2025Q1")

        cmd, params = session.commands[-1]
        assert "confidence" not in params

    def test_source_string_includes_excerpt(self):
        resolver = _MockResolver()
        session = _MockSession()
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation()
        importer._process_relation(session, rel, "2025Q1")

        cmd, params = session.commands[-1]
        assert "transcript:TST-2025Q1" in params["source"]

    def test_confidence_escalation_upgrades(self):
        resolver = _MockResolver()
        session = _MockSession()
        session.set_existing("c01", "m01", confidence="associated")
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({
            "relation_type": ":SUPPLIES_TO",
            "evidence_quality": "implicit",
            "valid_from": "2025-01-01",
            "subject_entity": {"name": "Nutrien", "type": "company"},
            "object_entity": {"name": "Potash", "type": "commodity"},
        })

        importer._process_relation(session, rel, "2025Q1")

        assert importer.stats["escalated"] == 1
        assert "inferred" in str(session.commands[-1])

    def test_no_escalation_when_existing_has_valid_until(self):
        resolver = _MockResolver()
        session = _MockSession()
        session.set_existing("c01", "m01", confidence="associated", valid_until="2025-06-01")
        driver = _MockDriver(session)
        importer = EarningsCallImporter(driver, resolver)

        rel = _make_relation({
            "relation_type": ":SUPPLIES_TO",
            "evidence_quality": "explicit",
            "subject_entity": {"name": "Nutrien", "type": "company"},
            "object_entity": {"name": "Potash", "type": "commodity"},
        })

        importer._process_relation(session, rel, "2025Q1")

        assert importer.stats["escalated"] == 0


class _MockDriver:
    def __init__(self, session):
        self._session = session

    def session(self):
        return self._session
