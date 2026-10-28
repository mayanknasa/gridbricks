# Standing Project Rules

All agents and contributors must adhere to these project rules:

1. **Architecture & Tech Stack**:
   - Monorepo structured with:
     - `backend/`: Python 3.12, FastAPI, pandas, pytest.
     - `frontend/`: React, TypeScript, Vite.

2. **Type Safety**:
   - Full type hints everywhere in Python.
   - Strict TypeScript configuration across the frontend.

3. **Models & Testing**:
   - Every API response must use a Pydantic model.
   - Every data logic function must have unit tests.

4. **Code Cleanliness & Design**:
   - Keep functions small and pure where possible.
   - No dead code and no unused dependencies.

5. **Timezone Handling**:
   - All timestamps and times must be handled as timezone-aware UTC internally.
   - Convert to UK local time only for display.

6. **Change Management & Communication**:
   - Make small, focused changes.
   - After each task, summarise what changed and explicitly list any assumptions made.

7. **External API Fidelity**:
   - Never invent API fields.
   - If unsure about the Elexon schema, fetch a real sample and inspect it.
