---
title: Build fit rule summary
domain: build
content_type: rule
summary: Build advice should compare account readiness, reusable gear, role needs, transition cost, and patch freshness.
linked_entities: gw2:system:build
linked_actions: generate_daily_plan
confidence: 0.78
review_status: reviewed
---
Build Fit Advisor should explain whether a build is practical for the current account, not just whether the build is popular.

Evaluation notes:

- prefer low-friction options for returning players;
- explain reusable gear and missing gear separately;
- include transition cost estimates when available;
- preserve build source attribution;
- warn when patch freshness is uncertain.

## Upgrade Effect Evidence Notes

Rune, sigil, and relic effect-family labels are conservative review hints. They should help explain broad fit categories, not claim a best-in-slot meta result.

Reviewed effect families:

- `power_damage`: power, berserker, precision, ferocity, scholar, force, and impact text.
- `condition_damage`: condition, viper, afflicted, nightmare, torment, bleeding, and burning text.
- `boon_support`: boon, concentration, leadership, divinity, quickness, and alacrity text.
- `healing_support`: healing, water, monk, magi, and harrier text.
- `defensive_survival`: durability, soldier, defense, sanctuary, protection, vitality, and toughness text.

These labels must remain informational. They do not replace source build verification, patch review, or manual in-game gear decisions.
