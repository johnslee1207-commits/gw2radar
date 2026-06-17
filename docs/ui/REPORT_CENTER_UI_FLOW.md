# Report Center UI Flow

## User Intent

A player wants a durable artifact after previewing or unlocking a report.

## Flow

1. Open `Reports`.
2. Load available products.
3. Load pricing plans.
4. Run mock checkout for development entitlement testing.
5. Generate a report from Returner, Legendary, Market, or Build Fit views.
6. Paste job id to inspect status.
7. Paste artifact id to open the exported report.

## Output Expectations

- Products and pricing come from backend configuration.
- Mock checkout is only a development payment abstraction.
- Report jobs preserve product id, goal id, format, and artifact references.
