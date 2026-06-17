# Privacy Safety UI Flow

## User Intent

A player wants to understand and control private data before trusting account-aware recommendations.

## Flow

1. Open `Privacy`.
2. Review private data and gameplay safety boundaries.
3. Delete API key when desired.
4. Delete account snapshot when desired.
5. Check key status after deletion.

## Output Expectations

- The raw API key is never rendered in UI output.
- Deletion controls call backend delete endpoints.
- Public KB and private account data are described as separate layers.
- The UI repeats no automation and no automatic trading boundaries.
