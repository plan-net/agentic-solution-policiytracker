# Test Command

Run smart testing for the Political Monitoring Agent v0.2.0 with optional scope parameter:

**Usage**: `/test [scope]` where scope can be: `unit`, `integration`, `etl`, `chat`, `coverage`, or `all` (default)

**Process**:
1. Always run code quality checks first: `just format && just typecheck`
2. Based on the scope parameter:
   - `unit`: Run `uv run pytest tests/unit/ -v`
   - `integration`: Run `uv run pytest tests/integration/ -v`
   - `etl`: Run `uv run pytest -k "etl" -v` (ETL pipeline tests)
   - `chat`: Run `uv run pytest -k "chat" -v` (Chat interface tests)
   - `coverage`: Run `uv run pytest --cov=src --cov-report=html --cov-report=term`
   - `all` or no parameter: Run `uv run pytest -v`
3. Show clear progress messages with emojis (🧪, 🔬, 🤖, 🔗, 📊)
4. If tests fail, provide helpful guidance on next steps
5. For coverage runs, mention that detailed HTML report is available in `htmlcov/index.html`
6. For ETL tests, mention running `just etl-status` to check Airflow health
7. For chat tests, mention checking `http://localhost:3000` to test the interface

Always run the pre-flight quality checks regardless of scope. Provide clear feedback on test results and any failures.