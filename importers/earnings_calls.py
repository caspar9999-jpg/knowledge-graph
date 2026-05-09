from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from neo4j import GraphDatabase

from importers.common import EntityResolver, MATCH_STATUS_UNMATCHED

logger = logging.getLogger(__name__)

RELATION_TYPE_MAP = {
    ":PROVIDES": "提供",
    ":SUPPLIES_TO": "供应给",
    ":USED_IN": "用于",
}

CONFIDENCE_MAP = {
    "explicit": "confirmed",
    "implicit": "inferred",
    "speculative": "associated",
}

COMMERCIAL_TYPES = {"Company", "Commodity"}
NO_CONFIDENCE_TYPES = {"用于"}


def _build_source(rel: dict) -> str:
    src = rel.get("source", {}) or {}
    transcript_id = rel.get("transcript_id", "unknown")
    speaker = src.get("speaker") or "unknown"
    excerpt = (src.get("excerpt") or "")[:120]
    excerpt = excerpt.replace('"', "'")
    return f'transcript:{transcript_id}|speaker:{speaker}|excerpt:"{excerpt}"'


def _extract_quarter(filepath: str) -> str:
    match = re.search(r"relations_(\d{4}Q[1-4])\.jsonl", filepath)
    if match:
        return match.group(1)
    raise ValueError(f"Cannot extract quarter from path: {filepath}")


def _confidence_level(level: str) -> int:
    return {"confirmed": 3, "inferred": 2, "associated": 1}.get(level, 0)


class EarningsCallImporter:
    def __init__(
        self,
        driver: GraphDatabase.driver,
        entity_resolver: EntityResolver,
    ) -> None:
        self._driver = driver
        self._resolver = entity_resolver
        self.stats = {
            "processed": 0,
            "skipped_division": 0,
            "skipped_termination": 0,
            "review_flagged": 0,
            "escalated": 0,
        }

    def process_file(self, filepath: str) -> dict:
        quarter = _extract_quarter(filepath)
        with self._driver.session() as session:
            self._resolver.load_cache(session)
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rel = json.loads(line)
                    self._process_relation(session, rel, quarter)
        return dict(self.stats)

    def _process_relation(
        self, session, rel: dict, quarter: str
    ) -> None:
        self.stats["processed"] += 1

        subject_type = rel.get("subject_entity", {}).get("type", "")
        object_type = rel.get("object_entity", {}).get("type", "")

        if subject_type == "division" or object_type == "division":
            self.stats["skipped_division"] += 1
            logger.info(
                "Skipping relation %s: DIVISION entity not supported",
                rel.get("relation_id", "unknown"),
            )
            return

        if rel.get("is_termination"):
            self.stats["skipped_termination"] += 1
            logger.info(
                "Skipping relation %s: termination requires manual review",
                rel.get("relation_id", "unknown"),
            )
            return

        subject_result = self._resolver.resolve(
            rel["subject_entity"]["name"],
            subject_type,
            session=session,
        )
        object_result = self._resolver.resolve(
            rel["object_entity"]["name"],
            object_type,
            session=session,
        )

        kg_rel_type = RELATION_TYPE_MAP.get(rel["relation_type"], "供应给")

        source = _build_source(rel)

        evidence = (rel.get("evidence_quality") or "").lower()
        kg_confidence = CONFIDENCE_MAP.get(evidence, "inferred")

        if kg_rel_type == "供应给":
            if not evidence or evidence == "speculative":
                kg_confidence = "associated"
            elif evidence == "explicit":
                kg_confidence = "inferred"

        if kg_rel_type == "提供":
            if evidence == "speculative":
                kg_confidence = "associated"

        needs_review = False
        if kg_rel_type == "供应给":
            valid_from = rel.get("valid_from")
            if not valid_from:
                kg_confidence = "associated"
                needs_review = True

        self._merge_edge(
            session,
            from_id=subject_result.node_id,
            to_id=object_result.node_id,
            rel_type=kg_rel_type,
            kg_confidence=kg_confidence,
            needs_review=needs_review,
            source=source,
            rel_id=rel.get("relation_id", ""),
            subject_matched=subject_result.match_status,
            object_matched=object_result.match_status,
        )

        self._handle_generalization(
            session, rel, subject_result, object_result
        )

    def _merge_edge(
        self,
        session,
        from_id: str | None,
        to_id: str | None,
        rel_type: str,
        kg_confidence: str,
        needs_review: bool,
        source: str,
        rel_id: str,
        subject_matched: str,
        object_matched: str,
    ) -> None:
        if not from_id or not to_id:
            logger.warning("Cannot write edge %s: missing endpoint", rel_id)
            return

        if rel_type == "用于":
            session.run(
                """MATCH (from {id: $from_id})
                   MATCH (to {id: $to_id})
                   MERGE (from)-[r:用于]->(to)
                   SET r.source = $source,
                       r.needs_review = $needs_review,
                       r.relation_id = $rel_id""",
                from_id=from_id,
                to_id=to_id,
                source=source,
                needs_review=needs_review,
                rel_id=rel_id,
            )
            return

        if rel_type == "提供":
            session.run(
                """MATCH (from {id: $from_id})
                   MATCH (to {id: $to_id})
                   MERGE (from)-[r:提供]->(to)
                   SET r.confidence = $confidence,
                       r.source = $source,
                       r.needs_review = $needs_review,
                       r.relation_id = $rel_id""",
                from_id=from_id,
                to_id=to_id,
                confidence=kg_confidence,
                source=source,
                needs_review=needs_review,
                rel_id=rel_id,
            )
            return

        # Check existing edge for escalation
        existing = session.run(
            """MATCH (from {id: $from_id})-[r:供应给]->(to {id: $to_id})
               RETURN r.confidence AS confidence, r.valid_until AS valid_until""",
            from_id=from_id,
            to_id=to_id,
        ).single()

        if existing:
            existing_conf = existing.get("confidence") or "associated"
            existing_valid_until = existing.get("valid_until")

            if existing_valid_until is not None:
                logger.info(
                    "Skipping confidence escalation for %s->%s: existing edge has valid_until",
                    from_id,
                    to_id,
                )
                return

            if _confidence_level(kg_confidence) > _confidence_level(existing_conf):
                self.stats["escalated"] += 1
                session.run(
                    """MATCH (from {id: $from_id})-[r:供应给]->(to {id: $to_id})
                       SET r.confidence = $confidence,
                           r.source = $source,
                           r.needs_review = $needs_review,
                           r.relation_id = $rel_id""",
                    from_id=from_id,
                    to_id=to_id,
                    confidence=kg_confidence,
                    source=source,
                    needs_review=needs_review,
                    rel_id=rel_id,
                )
            else:
                logger.debug(
                    "Not escalating %s->%s: %s <= existing %s",
                    from_id,
                    to_id,
                    kg_confidence,
                    existing_conf,
                )
            return

        # New edge
        session.run(
            """MATCH (from {id: $from_id})
               MATCH (to {id: $to_id})
               MERGE (from)-[r:供应给]->(to)
               SET r.confidence = $confidence,
                   r.source = $source,
                   r.needs_review = $needs_review,
                   r.relation_id = $rel_id""",
            from_id=from_id,
            to_id=to_id,
            confidence=kg_confidence,
            source=source,
            needs_review=needs_review,
            rel_id=rel_id,
        )

    def _handle_generalization(
        self,
        session,
        rel: dict,
        subject_result,
        object_result,
    ) -> None:
        for result, entity in [
            (subject_result, rel.get("subject_entity", {})),
            (object_result, rel.get("object_entity", {})),
        ]:
            if not result.node_id or not result.node_label:
                continue
            if result.node_label != "Product" and result.node_label != "Commodity":
                continue
            if result.match_status == MATCH_STATUS_UNMATCHED:
                self._assign_category(session, result, entity)

    def _assign_category(
        self, session, result, entity: dict
    ) -> None:
        existing_categories = session.run(
            "MATCH (n {id: $id}) RETURN n.categories AS categories",
            id=result.node_id,
        ).single()
        if existing_categories and existing_categories.get("categories"):
            return

        parent = session.run(
            """MATCH (n {id: $id})-[:归类于]->(cat:ProductCategory)
               RETURN cat.name AS name LIMIT 1""",
            id=result.node_id,
        ).single()
        if parent:
            session.run(
                "MATCH (n {id: $id}) SET n.categories = $categories",
                id=result.node_id,
                categories=[parent["name"]],
            )
