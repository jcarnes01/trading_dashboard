# SPX Morning Playbook & Options Trading Dashboard

A real-time options and macro decision-support dashboard for active traders. Ingests intermarket macro signals and index options chain structure to compute structural dealer boundaries, expected moves, directional bias scores, and trade playbook recommendations.

## Documentation & Architecture

For the complete architectural design, domain models, component breakdown, and refactoring plan, see:
- [System Architecture Document (ARCHITECTURE.md)](ARCHITECTURE.md)

## Tech Stack
- **Language:** Python 3.10+
- **Frontend / Presentation:** Streamlit
- **Data Ingestion:** Yahoo Finance (`yfinance`) with pluggable provider architecture
- **Data Analysis:** Pandas, NumPy
- **Quality & Testing:** Pytest, Ruff, Mypy
