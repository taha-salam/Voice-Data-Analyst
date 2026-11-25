# Voice Data Analyst

An end-to-end voice-driven business intelligence tool that enables conversational querying of relational databases (SQLite, PostgreSQL, DuckDB/CSV) using natural spoken English. Built for Fall 2026 NLP Course Project.

## Project Details
- **Student Name:** Taha Salam
- **Registration Number:** [Enter Registration Number]
- **Project Selected:** Project 4 - Voice Data Analyst

## Architecture & Technology Stack
- **Local Speech-to-Text (ASR):** `faster-whisper` (`base.en` / `int8` CPU quantization) — 100% offline.
- **Local Text-to-Speech (TTS):** `pyttsx3` (native OS SAPI5) — 100% offline.
- **LLM Engine:** Groq API (`openai/gpt-oss-120b`) for ultra-low latency SQL generation and query reasoning.
- **Data Engines:** Multi-source support for SQLite, PostgreSQL connection strings, and DuckDB (in-memory CSV/parquet querying).
- **Security & Safety:** AST-based SQL validation using `sqlglot` strictly enforcing read-only `SELECT` queries and preventing SQL injection and destructive commands (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`).
- **Self-Repair:** Autonomous query error correction loop with max 3 retry attempts.
- **Domain Word Correction:** Real-time fuzzy and phonetic token alignment against active database categorical values.

## Quickstart

### 1. Setup Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
GROQ_MODEL=openai/gpt-oss-120b
WHISPER_MODEL_SIZE=base.en
TTS_ENGINE=pyttsx3
```

### 3. Run Automated Tests
```bash
pytest -v
```
