# Graph Pipeline

MVP 0.1 pipeline:

```text
Mock fixtures -> GraphData -> Goal gap -> Material policy -> Action generation -> Markdown report
```

SQLite SQLAlchemy models are provided for the persistence shape. Runtime tests use the deterministic in-memory graph to keep the mock loop small and repeatable.
