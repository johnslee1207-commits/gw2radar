# Attribute Schema

Entity and relation attributes are stored as JSON dictionaries for MVP 0.1.

Important attributes:

- goal.requirements: required entity ids and quantities.
- item.tradable: whether an item can be traded.
- item.legendary_related: whether default policy should avoid SELL_SURPLUS.
- task.produces: produced entity ids and estimated quantities.
- task.estimated_minutes: rough manual time estimate.
- action.priority_score: ranked recommendation score from 0.0 to 1.0.
- action.explanation: human-readable reason required for every action.
