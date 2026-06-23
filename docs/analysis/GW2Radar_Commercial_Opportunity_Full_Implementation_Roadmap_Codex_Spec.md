# GW2Radar Commercial Opportunity Full Implementation Roadmap — Codex Spec

```text
Document ID: GW2RADAR_COMMERCIAL_OPPORTUNITY_FULL_IMPLEMENTATION_ROADMAP_CODEX_SPEC
Project: GW2Radar
Version: v0.3-commercial-planning
Status: Draft for Codex / Product / Commercial Implementation
Primary Audience:
  - Codex
  - Product Owner
  - Backend Developer
  - Architecture Reviewer
  - Growth / Commercial Operator
```

---

## 0. Purpose

This document defines the post-foundation commercial product roadmap for **GW2Radar**, with the goal of implementing all identified business opportunities in a compliant, evidence-backed, and production-safe way.

GW2Radar's commercial value is not selling official API data. Its value is:

```text
Player-authorized account state
+ public GW2 knowledge
+ game ontology
+ knowledge graph
+ goal inference
+ action recommendation
+ evidence-backed reports
+ subscription-grade decision intelligence
```

The commercial modules must remain compliant with the GW2Radar constitution:

```text
1. No gameplay automation.
2. No client memory reading.
3. No automated trading.
4. No RMT support.
5. No API rate-limit evasion.
6. No proxy pool.
7. No private player data leakage.
8. No guaranteed-profit language.
9. Every important recommendation must be explainable.
10. Every important conclusion must be evidence-backed.
```

---

## 1. Commercial Opportunity Map

GW2Radar should implement the following monetizable product lines:

```text
P6  Paid Report Engine
P7  Legendary Planner Pro
P8  Build Fit & Gear Transition Advisor
P9  Market Radar Pro
P10 Guild / Static Readiness Console
P11 Creator & Community Intelligence Console
P12 Growth Website + SEO + CMS + Payment
P13 Subscription / Analytics / Commercial Dashboard
P14 v1.0 Personal Game Intelligence Platform
```

Summary:

```text
P6  converts reports into paid products.
P7  monetizes legendary planning.
P8  differentiates through account-specific build fit.
P9  adds senior-player market intelligence.
P10 opens guild/team subscription opportunities.
P11 serves creators and community operators.
P12 creates acquisition, pricing, CMS, and payment foundation.
P13 creates business analytics and retention insight.
P14 integrates all capabilities into a complete platform.
```

---

## 2. Engineering Prerequisites

Before commercial modules are exposed to real users, these foundation milestones must be complete or intentionally mocked for private testing:

```text
P0 Durable Refresh Queue
P1 Official GW2 API Compatibility Hardening
P2 Account Snapshot Sync Pipeline
P3 Public Static Data Refresh Worker
P5 Production Security Upgrade
```

Minimum production requirement:

```text
P0 + P1 + P2 + P5
```

Recommended commercial implementation order:

```text
Foundation:
P0 → P1 → P2 → P3 → P5

Commercial:
P6 → P7 → P8 → P9 → P12 → P10 → P11 → P13 → P14
```

---

## 3. Commercial Packaging Strategy

### 3.1 Free Tier

Purpose:

```text
Lead generation and trust building.
```

Capabilities:

```text
1. Basic account readiness preview.
2. One active goal summary.
3. Top 3 recommendations.
4. Limited do-not-sell warning.
5. Basic report preview.
```

### 3.2 Paid One-Time Report

Purpose:

```text
Immediate monetization through high-value reports.
```

Products:

```text
1. Returner Account Diagnosis Report.
2. Legendary Goal Gap Report.
3. Build Fit Report.
4. Market Snapshot Report.
```

### 3.3 Personal Subscription

Purpose:

```text
Recurring revenue from serious players.
```

Capabilities:

```text
1. Multi-goal planning.
2. Weekly reports.
3. Build fit analysis.
4. Market watchlist.
5. Patch impact alerts.
6. Advanced exports.
```

### 3.4 Guild / Team Subscription

Purpose:

```text
Higher-value B2B-style subscription.
```

Capabilities:

```text
1. Team readiness.
2. Role coverage.
3. Member consent workflow.
4. Static / guild reports.
5. Training suggestions.
```

### 3.5 Creator / Community Tier

Purpose:

```text
Serve content creators, guide writers, and community managers.
```

Capabilities:

```text
1. Topic trends.
2. Guide gap analysis.
3. Patch content opportunity.
4. Returner FAQ opportunities.
5. Weekly creator report.
```

---

# P6 — Paid Report Engine

## 4. P6 Commercial Goal

P6 turns existing report generation into a monetizable product system.

It supports:

```text
free previews
paid full reports
subscription reports
export jobs
report entitlements
report artifacts
```

P6 should be the first commercial module after security and account sync foundation.

## 5. P6 Scope

### 5.1 In Scope

```text
1. ReportProduct model.
2. ReportTier model.
3. ReportEntitlement model.
4. ReportExportJob model.
5. Free vs paid rendering modes.
6. Preview report generation.
7. Full report generation.
8. Markdown and HTML exports.
9. PDF export stub or interface.
10. Report artifact manifest.
11. API endpoints for product list, preview, generation, job status, and artifact download.
```

### 5.2 Out of Scope

```text
1. Real payment provider integration, unless P12 is included.
2. Automated gameplay.
3. Automated trading.
4. Raw private data export.
5. PDF rendering if no rendering pipeline exists.
```

## 6. P6 Data Models

```yaml
ReportProduct:
  product_id: string
  name: string
  report_type: legendary | returner | build_fit | market | guild | creator
  tier: free | paid_once | subscription
  price_cents: int | null
  enabled: bool

ReportEntitlement:
  entitlement_id: string
  user_id: string
  product_id: string
  entitlement_type: preview | full | subscription
  valid_until: datetime | null
  created_at: datetime

ReportExportJob:
  job_id: string
  user_id: string
  report_type: string
  format: markdown | html | pdf | zip
  status: queued | processing | succeeded | failed
  artifact_path: string | null
  manifest_path: string | null
  created_at: datetime
  updated_at: datetime
```

## 7. P6 API Endpoints

```http
GET  /api/v1/reports/products
POST /api/v1/reports/preview
POST /api/v1/reports/generate
GET  /api/v1/reports/jobs/{job_id}
GET  /api/v1/reports/artifacts/{artifact_id}
```

## 8. P6 Codex Prompt

```text
Current project: GW2Radar

Implement P6: Paid Report Engine.

Prerequisites:
- P4 Returner Report or existing MVP report generator.
- P5 Production Security Upgrade if handling real users.

Implement:
1. ReportProduct model.
2. ReportEntitlement model.
3. ReportExportJob model.
4. Free vs paid report rendering mode.
5. Report preview generator.
6. Full report generator.
7. Markdown and HTML export.
8. PDF export interface or stub.
9. Report artifact manifest.
10. API endpoints:
   - GET /api/v1/reports/products
   - POST /api/v1/reports/preview
   - POST /api/v1/reports/generate
   - GET /api/v1/reports/jobs/{job_id}
   - GET /api/v1/reports/artifacts/{artifact_id}

Hard constraints:
- No API key in reports.
- No raw private account payload in reports.
- No gameplay automation.
- No automated trading.
- Free report must not expose paid-only details.
- Paid report must remain evidence-backed.
- Report artifacts must respect user deletion policy.

Tests:
- test_report_product_model.py
- test_report_entitlement.py
- test_free_report_preview.py
- test_paid_report_full.py
- test_report_export_job.py
- test_report_no_secret_leakage.py
```

---

# P7 — Legendary Planner Pro

## 9. P7 Commercial Goal

P7 deepens the most obvious individual-player monetization use case:

```text
Legendary planning.
```

It should answer:

```text
Which legendary should I prioritize?
What am I missing?
Which materials should I reserve?
Which materials can I sell?
What is the cheapest path?
What is the fastest path?
What should I do daily and weekly?
```

## 10. P7 Core Features

```text
1. Multi-legendary goal portfolio.
2. Goal priority.
3. Goal conflict analysis.
4. Shared material pool.
5. Time-gated requirement detection.
6. Map currency planning.
7. Daily/weekly progress route.
8. Goal cost index.
9. Cheapest path.
10. Fastest path.
11. Multi-goal do-not-sell policy.
```

## 11. P7 New Entities

```text
LegendaryGoal
GoalPortfolio
SharedRequirement
TimeGate
AcquisitionMethod
CostPath
FastPath
CheapPath
GoalConflict
GoalPriority
MaterialReservation
```

## 12. P7 New Relations

```text
GOAL_SHARES_REQUIREMENT_WITH
GOAL_CONFLICTS_WITH
GOAL_HAS_TIME_GATE
ITEM_ACQUIRED_BY
CURRENCY_ACQUIRED_BY
ACTION_ADVANCES_MULTIPLE_GOALS
GOAL_HAS_CHEAP_PATH
GOAL_HAS_FAST_PATH
ITEM_RESERVED_FOR_GOAL_PORTFOLIO
```

## 13. P7 Report

```text
Legendary Planner Pro Report
├── Active legendary portfolio
├── Recommended goal priority
├── Total missing materials
├── Shared material conflicts
├── Time-gated requirements
├── Daily route
├── Weekly route
├── Cheapest path
├── Fastest path
├── Do-not-sell list
└── Estimated completion window
```

## 14. P7 Codex Prompt

```text
Implement P7: Legendary Planner Pro.

Prerequisites:
- MVP 0.1 Goal Gap.
- P2 Account Snapshot Sync.
- P3 Public Static Data Refresh.
- P6 Report Engine.

Implement:
1. GoalPortfolio model.
2. LegendaryGoal model extension.
3. SharedRequirement inference.
4. TimeGate model.
5. AcquisitionMethod model.
6. CheapPath and FastPath inference.
7. Multi-goal material reservation.
8. Do-not-sell policy across all active goals.
9. Daily/weekly legendary action planner.
10. Legendary Planner Pro report template.

API endpoints:
- POST /api/v1/legendary/goals
- GET /api/v1/legendary/portfolio
- POST /api/v1/legendary/recompute
- GET /api/v1/legendary/do-not-sell
- POST /api/v1/legendary/report

Hard constraints:
- No gameplay automation.
- No automated farming.
- No automated trading.
- Recommendations only.
- All material policies must be explainable.
- Paid report must not expose API key or raw private payload.

Tests:
- test_goal_portfolio.py
- test_shared_requirements.py
- test_goal_conflicts.py
- test_time_gate_inference.py
- test_do_not_sell_multi_goal.py
- test_cheap_path.py
- test_fast_path.py
- test_legendary_pro_report.py
```

---

# P8 — Build Fit & Gear Transition Advisor

## 15. P8 Commercial Goal

P8 provides GW2Radar's major differentiation from public build websites.

Public build websites answer:

```text
How is this build configured?
```

GW2Radar answers:

```text
Can my account play this build now?
What am I missing?
How much will conversion cost?
What gear can I reuse?
Is there a cheaper alternative?
```

## 16. P8 Core Features

```text
1. Build import.
2. Build Requirement Graph.
3. Account Gear Matcher.
4. Build Fit Score.
5. Gear Transition Cost.
6. Budget Alternative.
7. Playable Now indicator.
8. Patch Freshness Warning.
```

## 17. P8 New Entities

```text
Build
BuildSource
BuildVariant
Profession
Specialization
Role
GameMode
GearRequirement
GearSlot
StatCombo
Rune
Sigil
Relic
WeaponSet
BuildFitScore
GearTransitionPlan
```

## 18. P8 Build Fit Score

```text
BuildFitScore =
  0.30 * gear_match
+ 0.20 * unlock_match
+ 0.15 * cost_affordability
+ 0.15 * difficulty_match
+ 0.10 * preferred_mode_match
+ 0.10 * patch_freshness
```

## 19. P8 API Endpoints

```http
POST /api/v1/builds/import
GET  /api/v1/builds
POST /api/v1/builds/fit
POST /api/v1/builds/transition-plan
POST /api/v1/builds/report
```

## 20. P8 Codex Prompt

```text
Implement P8: Build Fit & Gear Transition Advisor.

Prerequisites:
- P2 Account Snapshot Sync.
- P3 Public Static Data Refresh.
- P6 Report Engine.
- P5 Security Upgrade for real users.

Implement:
1. Build entity model.
2. BuildRequirement schema.
3. GearRequirement model.
4. AccountGearSnapshot model.
5. GearMatcher.
6. BuildFitScore calculator.
7. GearTransitionCost estimator.
8. BudgetAlternative recommender.
9. BuildFit report template.
10. API endpoints:
   - POST /api/v1/builds/import
   - GET /api/v1/builds
   - POST /api/v1/builds/fit
   - POST /api/v1/builds/transition-plan
   - POST /api/v1/builds/report

Hard constraints:
- Do not scrape third-party sites aggressively.
- Use manual Build URL import or structured mock data first.
- Preserve source attribution.
- Do not claim absolute meta authority.
- Mark stale Build data.
- No gameplay automation.
- No automatic gear change.

Tests:
- test_build_requirement_schema.py
- test_account_gear_matcher.py
- test_build_fit_score.py
- test_gear_transition_cost.py
- test_budget_alternative.py
- test_build_report.py
- test_build_source_attribution.py
```

---

# P9 — Market Radar Pro

## 21. P9 Commercial Goal

P9 is a senior-player subscription feature.

It provides:

```text
goal material price observation
legendary cost trend
account-safe sell candidate analysis
material retention advice
market anomaly alerts
```

It must not become a trading bot.

## 22. P9 Core Features

```text
1. Price Snapshot.
2. Price Trend.
3. Goal Cost Index.
4. Material Watchlist.
5. Surplus Sell Candidate.
6. Hold Candidate.
7. Buy Wait Suggestion.
8. Market Report.
```

## 23. P9 New Entities

```text
MarketSnapshot
PricePoint
PriceTrend
GoalCostIndex
MarketSignal
ItemWatchlist
HoldCandidate
SellCandidate
VolatilityScore
LiquidityScore
```

## 24. P9 Market Boundary

Allowed language:

```text
suggest observing
suggest holding
consider selling surplus
price above recent average
required by active goal
```

Forbidden language:

```text
guaranteed profit
must buy now
sure win
arbitrage exploit
automated order
market manipulation
RMT
```

## 25. P9 API Endpoints

```http
GET  /api/v1/market/watchlist
POST /api/v1/market/watchlist
GET  /api/v1/market/goal-cost-index
GET  /api/v1/market/signals
POST /api/v1/market/report
```

## 26. P9 Codex Prompt

```text
Implement P9: Market Radar Pro.

Prerequisites:
- P3 Public Static Data Refresh.
- P7 Legendary Planner Pro.
- P6 Report Engine.

Implement:
1. MarketSnapshot model.
2. PricePoint model.
3. PriceTrend calculator.
4. GoalCostIndex calculator.
5. HoldCandidate inference.
6. SellCandidate inference.
7. Material Watchlist.
8. Market Radar Report.
9. API endpoints:
   - GET /api/v1/market/watchlist
   - POST /api/v1/market/watchlist
   - GET /api/v1/market/goal-cost-index
   - GET /api/v1/market/signals
   - POST /api/v1/market/report

Hard constraints:
- No automated trading.
- No order placement.
- No guaranteed-profit language.
- No RMT support.
- No high-frequency arbitrage.
- Respect GW2 API cache/rate limits.

Tests:
- test_price_snapshot.py
- test_price_trend.py
- test_goal_cost_index.py
- test_hold_candidate.py
- test_sell_candidate.py
- test_market_language_policy.py
- test_no_auto_trading.py
```

---

# P10 — Guild / Static Readiness Console

## 27. P10 Commercial Goal

P10 enables team and guild subscriptions.

Target users:

```text
Raid static
Strike static
WvW guild
Training guild
Community Discord
```

## 28. P10 Core Questions

```text
Which roles are missing?
Do we have Quickness / Alacrity / Healer coverage?
Are members prepared?
Which builds are missing?
What should the guild train this week?
```

## 29. P10 Privacy Rules

```text
1. Every member must explicitly authorize access.
2. Team report must show only necessary summary.
3. No cross-team leakage.
4. No raw bank/inventory exposure.
5. Members can revoke consent.
6. Consent revocation must remove team access to member data.
```

## 30. P10 New Entities

```text
Guild
Team
TeamMember
ConsentRecord
TeamRole
RoleCoverage
TeamGoal
TeamReadinessScore
MemberReadinessSummary
```

## 31. P10 API Endpoints

```http
POST /api/v1/guilds
POST /api/v1/teams
POST /api/v1/teams/{team_id}/members/invite
POST /api/v1/teams/{team_id}/readiness
GET  /api/v1/teams/{team_id}/report
POST /api/v1/teams/{team_id}/members/{member_id}/revoke
```

## 32. P10 Codex Prompt

```text
Implement P10: Guild / Static Readiness Console.

Prerequisites:
- P5 Production Security Upgrade.
- P8 Build Fit Advisor.
- P6 Report Engine.

Implement:
1. Guild model.
2. Team model.
3. TeamMember model.
4. ConsentRecord model.
5. TeamRole model.
6. RoleCoverage inference.
7. TeamReadinessScore.
8. MemberReadinessSummary.
9. Guild Readiness Report.
10. API endpoints:
   - POST /api/v1/guilds
   - POST /api/v1/teams
   - POST /api/v1/teams/{team_id}/members/invite
   - POST /api/v1/teams/{team_id}/readiness
   - GET /api/v1/teams/{team_id}/report

Hard constraints:
- No member data without consent.
- No cross-team leakage.
- Do not expose raw inventory/bank.
- Members can revoke consent.
- No gameplay automation.
- No automated team commands.

Tests:
- test_team_consent.py
- test_role_coverage.py
- test_team_readiness_score.py
- test_member_privacy_summary.py
- test_guild_report.py
- test_consent_revoke.py
```

---

# P11 — Creator & Community Intelligence Console

## 33. P11 Commercial Goal

P11 serves:

```text
YouTube creators
guide authors
Discord community managers
guild content leads
website operators
```

It finds:

```text
player pain points
guide gaps
patch topics
legendary route opportunities
returner FAQ topics
build controversy topics
```

## 34. P11 Content Boundary

Allowed:

```text
public links
titles
summaries
manual inputs
authorized content
low-frequency retrieval
source links
```

Avoid:

```text
mass full-text copying
unauthorized reposting
presenting third-party work as original
robots bypass
private Discord ingestion without authorization
```

## 35. P11 New Entities

```text
CommunitySignal
TopicTrend
QuestionCluster
GuideGap
ContentOpportunity
CreatorReport
AudienceSegment
```

## 36. P11 API Endpoints

```http
POST /api/v1/creator/signals/import
GET  /api/v1/creator/topics
GET  /api/v1/creator/opportunities
POST /api/v1/creator/report
```

## 37. P11 Codex Prompt

```text
Implement P11: Creator & Community Intelligence Console.

Prerequisites:
- P4 Returner Diagnosis.
- P5 Production Security.
- P8 Build Fit.
- P9 Market Radar.
- P6 Report Engine.

Implement:
1. CommunitySignal model.
2. TopicTrend model.
3. QuestionCluster model.
4. GuideGap model.
5. ContentOpportunity model.
6. CreatorReport.
7. Source attribution and confidence labels.
8. API endpoints:
   - POST /api/v1/creator/signals/import
   - GET /api/v1/creator/topics
   - GET /api/v1/creator/opportunities
   - POST /api/v1/creator/report

Hard constraints:
- Do not mass-copy third-party content.
- Preserve source links.
- Store summaries, not full copyrighted pages.
- Mark community-derived claims as low-confidence unless verified.
- No private Discord ingestion without explicit authorization.

Tests:
- test_community_signal.py
- test_topic_trend.py
- test_guide_gap.py
- test_content_opportunity.py
- test_creator_report.py
- test_source_attribution.py
- test_no_mass_copy.py
```

---

# P12 — Growth Website + SEO + CMS + Payment

## 38. P12 Commercial Goal

P12 turns the product into a market-facing business.

It provides:

```text
landing pages
SEO content
CMS
pricing
payment abstraction
entitlement integration
privacy and API key safety pages
```

## 39. P12 Website Structure

```text
Home
Returner Report Landing
Legendary Planner Landing
Build Fit Landing
Market Radar Landing
Guild Readiness Landing
Creator Intelligence Landing
Pricing
Docs
Privacy
Terms
API Key Safety
Blog / SEO Content
```

## 40. P12 CMS Features

```text
1. Landing page content.
2. Blog posts.
3. FAQ.
4. Pricing text.
5. Feature flags.
6. Report template descriptions.
7. SEO metadata.
```

## 41. P12 Payment Abstraction

Use an abstraction first:

```text
PaymentProvider
CheckoutSession
Subscription
Invoice
Entitlement
WebhookEvent
```

Do not lock the architecture to one payment provider in the domain model.

## 42. P12 Codex Prompt

```text
Implement P12: Growth Website + CMS + Payment Abstraction.

Prerequisites:
- P6 Paid Report Engine.
- P5 Security Upgrade.

Implement:
1. Public website routes.
2. Landing page models.
3. CMS content model.
4. Blog/FAQ model.
5. Pricing model.
6. Entitlement integration.
7. PaymentProvider interface.
8. MockPaymentProvider for tests.
9. CheckoutSession model.
10. Subscription model.
11. WebhookEvent model.
12. SEO metadata support.

Hard constraints:
- Do not claim affiliation with ArenaNet unless explicitly permitted.
- Do not sell official API access.
- Do not sell player data.
- Do not promise guaranteed in-game profit.
- Privacy and API key safety pages are mandatory.

Tests:
- test_landing_pages.py
- test_cms_content.py
- test_pricing_model.py
- test_payment_provider_mock.py
- test_entitlement_after_payment.py
- test_privacy_page_required.py
```

---

# P13 — Subscription / Analytics / Commercial Dashboard

## 43. P13 Commercial Goal

P13 creates the operating loop:

```text
Which reports convert?
Which features retain users?
Which user flows fail?
Which commercial module should be improved?
```

## 44. P13 Privacy Boundary

Allowed analytics:

```text
report type usage
feature clicks
conversion funnel
subscription status
error rates
export counts
anonymized goal type
```

Forbidden analytics:

```text
specific bank contents
specific account assets
API key
raw account name
cross-user private graph content
private inventory details
```

## 45. P13 New Entities

```text
EventTracking
ConversionFunnel
SubscriptionStatus
FeatureUsageMetric
ReportConversionMetric
CommercialDashboard
ChurnRiskIndicator
```

## 46. P13 Codex Prompt

```text
Implement P13: Subscription Analytics & Commercial Dashboard.

Prerequisites:
- P6 Report Engine.
- P12 Payment abstraction.
- P5 Security Upgrade.

Implement:
1. EventTracking model.
2. ConversionFunnel model.
3. SubscriptionStatus model.
4. CommercialDashboard API.
5. Privacy-safe analytics.
6. Feature usage metrics.
7. Report conversion metrics.
8. Churn risk indicator.

Hard constraints:
- No raw private account data in analytics.
- No API key in analytics.
- Use anonymized user id.
- No cross-user gameplay data exposure.
- User deletion must remove or anonymize analytics if required.

Tests:
- test_event_tracking_privacy.py
- test_conversion_funnel.py
- test_subscription_status.py
- test_commercial_dashboard.py
- test_no_private_data_in_analytics.py
```

---

# P14 — v1.0 Personal Game Intelligence Platform

## 47. P14 Goal

P14 integrates all commercial and intelligence capabilities into a complete platform.

## 48. v1.0 Capabilities

```text
1. Personal legendary planning.
2. Returner account diagnosis.
3. Build fit and gear transition.
4. Market radar.
5. Patch impact.
6. Daily / weekly planner.
7. Guild readiness.
8. Creator intelligence.
9. Paid reports.
10. Subscription system.
11. CMS / SEO / acquisition website.
12. Commercial analytics dashboard.
```

## 49. v1.0 Dashboard

```text
Dashboard
├── Active Goals
├── Today's Plan
├── Weekly Plan
├── Do-not-sell Materials
├── Build Fit Alerts
├── Market Watch
├── Patch Impact
├── Returner Recovery
├── Reports
├── Subscription
└── Privacy / API Key
```

## 50. v1.0 Success Criteria

```text
1. User can generate a personal report with authorized API data.
2. User can select goals and receive action plans.
3. User can purchase or unlock full reports.
4. User can view build fit and gear transition cost.
5. User can view material hold/sell suggestions.
6. Guild can generate team readiness report.
7. Creator can generate topic opportunity report.
8. All critical recommendations are explainable.
9. All private data can be deleted.
10. No gameplay automation.
11. No automated trading.
12. No unauthorized data scraping.
```

---

## 51. Final Recommended Execution Order

Engineering foundation:

```text
P0 → P1 → P2 → P3 → P5
```

Commercial modules:

```text
P6 → P7 → P8 → P9 → P12 → P10 → P11 → P13 → P14
```

Fastest commercial validation path:

```text
P5 → P6 → P4 paid report → P7 Legendary Planner Pro
```

Strongest subscription path:

```text
P7 → P8 → P9
```

Team revenue path:

```text
P8 → P10
```

Creator/community path:

```text
P11 → P12 → P13
```

---

## 52. Commercial Funnel

Recommended funnel:

```text
Free Returner Preview
→ Paid Returner Report
→ Legendary Planner Subscription
→ Build Fit Add-on
→ Market Radar Pro
→ Guild / Creator higher-tier plans
```

---

## 53. Final Product Principle

GW2Radar must not monetize official API access or player data.

It monetizes:

```text
1. Decision intelligence.
2. Personal planning.
3. Evidence-backed reports.
4. Time saved.
5. Mistake avoidance.
6. Goal prioritization.
7. Team readiness.
8. Creator insights.
```

Final rule:

```text
Sell intelligence, not data.
Sell planning, not automation.
Sell clarity, not shortcuts.
```
