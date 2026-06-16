from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from gw2radar.db.models import CommunitySignalModel, utc_now


MAX_SUMMARY_CHARS = 700
MAX_RAW_CONTEXT_CHARS = 1200
LOW_CONFIDENCE_CAP = 0.5
MIN_CLUSTER_SIZE = 2

NO_MASS_COPY_BOUNDARY = (
    "Store summaries and source links only; do not store or reproduce third-party full text."
)


class CommunitySourceType(StrEnum):
    PUBLIC_FORUM = "public_forum"
    REDDIT = "reddit"
    WIKI = "wiki"
    YOUTUBE_COMMENT = "youtube_comment"
    DISCORD_PRIVATE = "discord_private"


class CommunitySignalKind(StrEnum):
    DISCUSSION = "discussion"
    QUESTION = "question"
    PAIN_POINT = "pain_point"
    BUILD_REQUEST = "build_request"
    MARKET_INTEREST = "market_interest"


class AudienceSegment(StrEnum):
    GENERAL = "general"
    RETURNING_PLAYER = "returning_player"
    LEGENDARY_PLANNER = "legendary_planner"
    BUILD_LEARNER = "build_learner"
    GUILD_LEADER = "guild_leader"
    CREATOR = "creator"


class CommunitySignalInput(BaseModel):
    source_type: CommunitySourceType
    source_url: HttpUrl
    title: str
    summary: str = Field(max_length=MAX_SUMMARY_CHARS)
    topic: str
    audience_segment: AudienceSegment = AudienceSegment.GENERAL
    signal_kind: CommunitySignalKind = CommunitySignalKind.DISCUSSION
    confidence: float = Field(default=0.4, ge=0.0, le=1.0)
    verified: bool = False
    authorized_source: bool = False
    raw_context: str | None = Field(default=None, exclude=True)


class CommunitySignal(BaseModel):
    signal_id: str
    source_type: CommunitySourceType
    source_url: str
    title: str
    summary: str
    topic: str
    audience_segment: AudienceSegment
    signal_kind: CommunitySignalKind
    confidence: float
    verified: bool
    authorized_source: bool
    created_at: datetime


class TopicTrend(BaseModel):
    topic: str
    signal_count: int
    average_confidence: float
    audience_segments: list[AudienceSegment]
    source_urls: list[str]
    confidence_note: str


class QuestionCluster(BaseModel):
    topic: str
    question_count: int
    representative_questions: list[str]
    source_urls: list[str]
    confidence_note: str = "community-derived unless separately verified"


class GuideGap(BaseModel):
    topic: str
    audience_segment: AudienceSegment
    reason: str
    supporting_signal_ids: list[str]
    source_urls: list[str]
    confidence: float


class ContentOpportunity(BaseModel):
    opportunity_id: str
    topic: str
    title: str
    audience_segment: AudienceSegment
    recommended_format: str
    rationale: str
    source_urls: list[str]
    supporting_signal_ids: list[str]
    confidence: float


class CreatorReport(BaseModel):
    topic_trends: list[TopicTrend]
    question_clusters: list[QuestionCluster]
    guide_gaps: list[GuideGap]
    content_opportunities: list[ContentOpportunity]
    policy_boundary: str = NO_MASS_COPY_BOUNDARY


def import_community_signal(session: Session, signal: CommunitySignalInput) -> CommunitySignal:
    validate_no_mass_copy(signal.summary, signal.raw_context)
    if signal.source_type == CommunitySourceType.DISCORD_PRIVATE and not signal.authorized_source:
        raise ValueError("Private Discord signals require explicit authorization.")

    confidence = signal.confidence if signal.verified else min(signal.confidence, LOW_CONFIDENCE_CAP)
    row = CommunitySignalModel(
        signal_id=f"community_signal_{uuid4().hex}",
        source_type=signal.source_type.value,
        source_url=str(signal.source_url),
        title=signal.title.strip(),
        summary=signal.summary.strip(),
        topic=_normalize_topic(signal.topic),
        audience_segment=signal.audience_segment.value,
        signal_kind=signal.signal_kind.value,
        confidence=round(confidence, 3),
        verified=signal.verified,
        authorized_source=signal.authorized_source,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _signal_from_model(row)


def list_community_signals(session: Session, topic: str | None = None) -> list[CommunitySignal]:
    query = session.query(CommunitySignalModel)
    if topic:
        query = query.filter(CommunitySignalModel.topic == _normalize_topic(topic))
    rows = query.order_by(CommunitySignalModel.created_at, CommunitySignalModel.title).all()
    return [_signal_from_model(row) for row in rows]


def calculate_topic_trends(session: Session) -> list[TopicTrend]:
    signals = list_community_signals(session)
    by_topic = _group_by_topic(signals)
    trends: list[TopicTrend] = []
    for topic, rows in by_topic.items():
        source_urls = _unique([signal.source_url for signal in rows])
        segments = sorted({signal.audience_segment for signal in rows}, key=lambda item: item.value)
        avg = sum(signal.confidence for signal in rows) / len(rows)
        trends.append(
            TopicTrend(
                topic=topic,
                signal_count=len(rows),
                average_confidence=round(avg, 3),
                audience_segments=segments,
                source_urls=source_urls,
                confidence_note=_confidence_note(rows),
            )
        )
    return sorted(trends, key=lambda trend: (-trend.signal_count, trend.topic))


def cluster_questions(session: Session) -> list[QuestionCluster]:
    question_signals = [
        signal
        for signal in list_community_signals(session)
        if signal.signal_kind == CommunitySignalKind.QUESTION or _looks_like_question(signal.title, signal.summary)
    ]
    clusters: list[QuestionCluster] = []
    for topic, rows in _group_by_topic(question_signals).items():
        if len(rows) < MIN_CLUSTER_SIZE:
            continue
        clusters.append(
            QuestionCluster(
                topic=topic,
                question_count=len(rows),
                representative_questions=[signal.title for signal in rows[:3]],
                source_urls=_unique([signal.source_url for signal in rows]),
            )
        )
    return sorted(clusters, key=lambda cluster: (-cluster.question_count, cluster.topic))


def find_guide_gaps(session: Session) -> list[GuideGap]:
    signals = list_community_signals(session)
    question_topics = {cluster.topic for cluster in cluster_questions(session)}
    gaps: list[GuideGap] = []
    for topic, rows in _group_by_topic(signals).items():
        pain_points = [signal for signal in rows if signal.signal_kind in {CommunitySignalKind.PAIN_POINT, CommunitySignalKind.QUESTION}]
        if topic not in question_topics and len(pain_points) < MIN_CLUSTER_SIZE:
            continue
        segment = _dominant_segment(rows)
        confidence = sum(signal.confidence for signal in rows) / len(rows)
        gaps.append(
            GuideGap(
                topic=topic,
                audience_segment=segment,
                reason=f"{topic} shows repeated questions or pain points without a dedicated guide signal.",
                supporting_signal_ids=[signal.signal_id for signal in rows],
                source_urls=_unique([signal.source_url for signal in rows]),
                confidence=round(confidence, 3),
            )
        )
    return sorted(gaps, key=lambda gap: (-len(gap.supporting_signal_ids), gap.topic))


def find_content_opportunities(session: Session) -> list[ContentOpportunity]:
    trends = {trend.topic: trend for trend in calculate_topic_trends(session)}
    opportunities: list[ContentOpportunity] = []
    for gap in find_guide_gaps(session):
        trend = trends.get(gap.topic)
        count = trend.signal_count if trend else len(gap.supporting_signal_ids)
        fmt = "beginner guide" if gap.audience_segment == AudienceSegment.RETURNING_PLAYER else "checklist report"
        opportunities.append(
            ContentOpportunity(
                opportunity_id=f"content_opportunity_{uuid4().hex}",
                topic=gap.topic,
                title=f"{gap.topic.title()} guide for {gap.audience_segment.value.replace('_', ' ')}",
                audience_segment=gap.audience_segment,
                recommended_format=fmt,
                rationale=f"{count} attributed community signals indicate unresolved demand.",
                source_urls=gap.source_urls,
                supporting_signal_ids=gap.supporting_signal_ids,
                confidence=gap.confidence,
            )
        )
    return sorted(opportunities, key=lambda item: (-len(item.supporting_signal_ids), item.topic))


def build_creator_report(session: Session) -> CreatorReport:
    return CreatorReport(
        topic_trends=calculate_topic_trends(session),
        question_clusters=cluster_questions(session),
        guide_gaps=find_guide_gaps(session),
        content_opportunities=find_content_opportunities(session),
    )


def render_creator_report(report: CreatorReport) -> str:
    lines = [
        "# Creator Intelligence Report",
        "",
        "## Topic Trends",
        *(
            [
                f"- {trend.topic}: {trend.signal_count} signals, confidence {trend.average_confidence:.2f}, sources: {', '.join(trend.source_urls)}"
                for trend in report.topic_trends
            ]
            or ["- No community signals imported."]
        ),
        "",
        "## Question Clusters",
        *(
            [
                f"- {cluster.topic}: {cluster.question_count} questions; examples: {' | '.join(cluster.representative_questions)}"
                for cluster in report.question_clusters
            ]
            or ["- No repeated question clusters yet."]
        ),
        "",
        "## Guide Gaps",
        *([f"- {gap.topic}: {gap.reason}" for gap in report.guide_gaps] or ["- No guide gaps detected."]),
        "",
        "## Content Opportunities",
        *(
            [
                f"- {opportunity.title}: {opportunity.recommended_format}; sources: {', '.join(opportunity.source_urls)}"
                for opportunity in report.content_opportunities
            ]
            or ["- No content opportunities detected."]
        ),
        "",
        "## Source Attribution",
        *sorted({f"- {url}" for trend in report.topic_trends for url in trend.source_urls}),
        "",
        "## Policy Boundary",
        f"- {report.policy_boundary}",
        "- Community-derived claims remain low-confidence unless verified against primary sources.",
        "- Private community sources require explicit authorization before import.",
    ]
    text = "\n".join(lines) + "\n"
    validate_no_forbidden_copy_markers(text)
    return text


def validate_no_mass_copy(summary: str, raw_context: str | None = None) -> None:
    if len(summary) > MAX_SUMMARY_CHARS:
        raise ValueError("Community signal summaries must stay brief and cannot store full copied text.")
    if raw_context and len(raw_context) > MAX_RAW_CONTEXT_CHARS:
        raise ValueError("Raw context is too long; store a concise summary and source link instead.")
    lower = f"{summary}\n{raw_context or ''}".lower()
    validate_no_forbidden_copy_markers(lower)


def validate_no_forbidden_copy_markers(text: str) -> None:
    forbidden_markers = ["full article copied", "verbatim transcript", "entire guide text"]
    lower = text.lower()
    for marker in forbidden_markers:
        if marker in lower:
            raise ValueError(f"No mass-copy policy violation: {marker}")


def _group_by_topic(signals: list[CommunitySignal]) -> dict[str, list[CommunitySignal]]:
    grouped: dict[str, list[CommunitySignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.topic, []).append(signal)
    return grouped


def _dominant_segment(signals: list[CommunitySignal]) -> AudienceSegment:
    counts: dict[AudienceSegment, int] = {}
    for signal in signals:
        counts[signal.audience_segment] = counts.get(signal.audience_segment, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].value))[0][0]


def _confidence_note(signals: list[CommunitySignal]) -> str:
    return "verified source present" if any(signal.verified for signal in signals) else "community-derived low-confidence signal"


def _looks_like_question(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return "?" in text or text.startswith("how ") or " how do " in text or " what should " in text


def _normalize_topic(topic: str) -> str:
    return " ".join(topic.strip().lower().split())


def _unique(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values))


def _signal_from_model(row: CommunitySignalModel) -> CommunitySignal:
    return CommunitySignal(
        signal_id=row.signal_id,
        source_type=CommunitySourceType(row.source_type),
        source_url=row.source_url,
        title=row.title,
        summary=row.summary,
        topic=row.topic,
        audience_segment=AudienceSegment(row.audience_segment),
        signal_kind=CommunitySignalKind(row.signal_kind),
        confidence=row.confidence,
        verified=row.verified,
        authorized_source=row.authorized_source,
        created_at=row.created_at,
    )
