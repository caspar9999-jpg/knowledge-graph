from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

STUB_ID_COUNTER: dict[str, int] = {}
MATCH_STATUS_MATCHED = "matched"
MATCH_STATUS_UNMATCHED = "unmatched"


def _slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


@dataclass
class CachedEntity:
    node_id: str
    label: str
    name: str
    aliases: list[str] = field(default_factory=list)
    slug: str = ""

    def __post_init__(self):
        if not self.slug:
            self.slug = _slug(self.name)


@dataclass
class ResolutionResult:
    node_id: str | None
    match_status: str
    node_label: str | None
    entity_name: str
    matched_via: str = ""
    stub_created: bool = False


class EntityResolver:
    def __init__(
        self,
        driver: GraphDatabase.driver | None = None,
        llm_client: object | None = None,
    ) -> None:
        self._driver = driver
        self._llm = llm_client
        self._cache: dict[str, list[CachedEntity]] = {}
        self._loaded = False

    def load_cache(self, session) -> None:
        self._cache.clear()
        for label in ("Company", "Product", "Commodity"):
            result = session.run(
                "MATCH (n:" + label + ") "
                "WHERE n.id IS NOT NULL "
                "RETURN n.id AS id, n.name AS name, n.aliases AS aliases, labels(n) AS labels"
            )
            for row in result:
                names = [row["name"]]
                if row["aliases"]:
                    names.extend(row["aliases"])
                ce = CachedEntity(
                    node_id=row["id"],
                    label=label,
                    name=row["name"],
                    aliases=[a for a in (row["aliases"] or [])],
                )
                for name_variant in names:
                    slug = _slug(name_variant)
                    if slug not in self._cache:
                        self._cache[slug] = []
                    self._cache[slug].append(ce)

        self._loaded = True
        logger.info(
            "EntityResolver cache loaded: %d slugs from %d nodes",
            len(self._cache),
            sum(len(v) for v in self._cache.values()),
        )

    def resolve(
        self, name: str, entity_type: str, session=None
    ) -> ResolutionResult:
        if not self._loaded:
            if session:
                self.load_cache(session)
            else:
                return ResolutionResult(
                    node_id=None,
                    match_status=MATCH_STATUS_UNMATCHED,
                    node_label=None,
                    entity_name=name,
                )

        slug = _slug(name)

        # Step 1: exact slug match
        if slug in self._cache:
            candidates = self._cache[slug]
            best = self._pick_best_candidate(candidates, entity_type)
            if best:
                return ResolutionResult(
                    node_id=best.node_id,
                    match_status=MATCH_STATUS_MATCHED,
                    node_label=best.label,
                    entity_name=name,
                    matched_via="slug",
                )

        # Step 2: LLM fallback (optional)
        if self._llm is not None:
            llm_result = self._llm_fallback(name, entity_type)
            if llm_result:
                return ResolutionResult(
                    node_id=llm_result.node_id,
                    match_status=MATCH_STATUS_MATCHED,
                    node_label=llm_result.label,
                    entity_name=name,
                    matched_via="llm",
                )

        # Step 3: No match — create stub if session is available
        if session:
            stub_id = self._create_stub(session, name, entity_type)
            if stub_id:
                return ResolutionResult(
                    node_id=stub_id,
                    match_status=MATCH_STATUS_UNMATCHED,
                    node_label=entity_type.capitalize(),
                    entity_name=name,
                    matched_via="stub",
                    stub_created=True,
                )

        return ResolutionResult(
            node_id=None,
            match_status=MATCH_STATUS_UNMATCHED,
            node_label=None,
            entity_name=name,
        )

    def _pick_best_candidate(
        self, candidates: list[CachedEntity], entity_type: str
    ) -> CachedEntity | None:
        type_map = {"company": "Company", "product": "Product", "commodity": "Commodity"}
        target_label = type_map.get(entity_type.lower(), entity_type.capitalize())

        exact = [c for c in candidates if c.label == target_label]
        if exact:
            return exact[0]

        if candidates:
            return candidates[0]

        return None

    def _llm_fallback(
        self, name: str, entity_type: str
    ) -> CachedEntity | None:
        if not self._llm:
            return None

        type_map = {"company": "Company", "product": "Product", "commodity": "Commodity"}
        target_label = type_map.get(entity_type.lower(), entity_type.capitalize())

        candidates_of_type = [
            ce for ce_list in self._cache.values() for ce in ce_list
            if ce.label == target_label
        ]

        if not candidates_of_type:
            return None

        prompt = (
            f"You are mapping extracted entity names to a knowledge graph catalog. "
            f"Given the extracted name '{name}' (type: {entity_type}), "
            f"which of the following catalog entries is the closest match?\n\n"
        )
        for ce in candidates_of_type:
            alias_str = f" (aliases: {', '.join(ce.aliases)})" if ce.aliases else ""
            prompt += f"- {ce.node_id}: {ce.name}{alias_str}\n"
        prompt += (
            "\nReturn ONLY the catalog ID (e.g., 'c01') of the best match, "
            "or 'none' if no match exists. Do not include any other text."
        )

        try:
            client = self._llm
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite", contents=prompt
            )
            answer = response.text.strip()

            for ce in candidates_of_type:
                if answer == ce.node_id:
                    return ce

            for ce in candidates_of_type:
                if ce.node_id in answer or answer in ce.node_id:
                    return ce

            return None

        except Exception as e:
            logger.warning("LLM fallback failed for '%s': %s", name, e)
            return None

    def _create_stub(
        self, session, name: str, entity_type: str
    ) -> str | None:
        type_map = {"company": "Company", "product": "Product", "commodity": "Commodity"}
        label = type_map.get(entity_type.lower(), entity_type.capitalize())

        global STUB_ID_COUNTER
        STUB_ID_COUNTER[label] = STUB_ID_COUNTER.get(label, 0) + 1
        stub_id = f"s_{label.lower()}_{STUB_ID_COUNTER[label]:04d}"

        try:
            if label == "Commodity":
                session.run(
                    "CREATE (n:Commodity:Product {id: $id, name: $name, "
                    "aliases: [], match_status: $match_status, "
                    "needs_review: true})",
                    id=stub_id, name=name, match_status=MATCH_STATUS_UNMATCHED
                )
            else:
                session.run(
                    "CREATE (n:" + label + " {id: $id, name: $name, "
                    "aliases: [], match_status: $match_status, "
                    "needs_review: true})",
                    id=stub_id, name=name, match_status=MATCH_STATUS_UNMATCHED
                )
            logger.info("Created stub entity %s (%s) for '%s'", stub_id, label, name)
            return stub_id
        except Exception as e:
            logger.error("Failed to create stub entity for '%s': %s", name, e)
            return None
