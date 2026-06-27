import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class EvidenceChainResult:
    chain_intact: bool
    total_links: int = 0
    broken_links: list[str] = field(default_factory=list)
    chain_hash: str = ""


class EvidenceBinder:
    def create_chain(self, evidence_ids: list[str], previous_hash: str = "") -> str:
        combined = previous_hash + "|" + "|".join(sorted(evidence_ids))
        return hashlib.sha256(combined.encode()).hexdigest()

    def verify_chain(self, chain_id: str, evidence_ids: list[str], expected_hash: str, previous_hash: str = "") -> EvidenceChainResult:
        actual_hash = self.create_chain(evidence_ids, previous_hash)
        links = sorted(evidence_ids)
        broken: list[str] = []
        for eid in links:
            if not eid or not isinstance(eid, str):
                broken.append(str(eid))
        return EvidenceChainResult(
            chain_intact=actual_hash == expected_hash and not broken,
            total_links=len(links),
            broken_links=broken,
            chain_hash=actual_hash,
        )

    def sign_evidence(self, payload: dict) -> str:
        raw = str(sorted(payload.items()))
        return hashlib.sha256(raw.encode()).hexdigest()
