# Graph Pipeline

MVP 0.1 pipeline:

```text
Mock fixtures -> GraphData -> SQLite -> GraphData -> Goal gap -> Material policy -> Action generation -> Markdown report
```

SQLite SQLAlchemy models persist the deterministic mock graph after `/mock/load`.
Inference still runs against `GraphData` so the rules stay isolated from database concerns.
