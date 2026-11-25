# Voice Data Analyst — System Architecture & Data Flow

## 1. High-Level Architecture Overview

The **Voice Data Analyst** is an end-to-end conversational business intelligence system. It combines offline local acoustic modeling with cloud LLM reasoning and zero-trust AST database security to allow non-technical business stakeholders to query multi-engine databases using spoken natural English.

```mermaid
flowchart TD
    subgraph ClientLayer ["1. Client & Speech Capture (In-Browser)"]
        UI["Streamlit UI (app.py)"]
        MIC["st.audio_input (Microphone Capture)"]
        AUDIO_WAV["Raw Audio Stream (16kHz WAV)"]
    end

    subgraph OfflineVoiceLayer ["2. Offline Local Speech Engine (Zero Cloud Audio APIs)"]
        ASR["faster-whisper (CTranslate2, int8 CPU)"]
        RAW_TRANSCRIPT["Raw Speech Transcript"]
        TTS["pyttsx3 (Native OS SAPI5 Voice Engine)"]
        AUDIO_OUT["Synthesized Voice Output (Audio Waveform)"]
    end

    subgraph NLPLayer ["3. NLP, Alignment & Intent Layer"]
        CORRECTOR["Domain Word Corrector (Phonetic & Levenshtein Alignment)"]
        CORRECTED_QUERY["Phonetically Corrected Query"]
        ROUTER["Multi-Source Router (SQLite / DuckDB / Postgres)"]
        PRUNER["Dynamic Schema Linker (Graph Bridge & Token Pruner)"]
        CLARIFIER["Clarification Engine (Ambiguity & Missing Granularity Detection)"]
        MEMORY["Conversational Memory (Multi-Turn Query Refinement)"]
    end

    subgraph LLMLayer ["4. LLM Generation & Reasoning (Groq API)"]
        LLM_SQL["Text-to-SQL Generator (openai/gpt-oss-120b)"]
        LLM_REPAIR["Autonomous Self-Repair Engine (Max 3 Retries)"]
        LLM_INSIGHT["Executive Analytics Summarizer (1-2 Spoken Sentences)"]
    end

    subgraph SecurityLayer ["5. Security & Safety Guardrails (Zero-Trust AST)"]
        AST_GUARD["sqlglot AST Parser (Read-Only SELECT Enforcement)"]
        INJ_GUARD["Prompt Injection & Multi-Statement Piggyback Filter"]
    end

    subgraph DataLayer ["6. Multi-Engine Databases"]
        OLIST_DB[("Primary DB: Olist Brazilian E-Commerce (SQLite)")]
        INV_DB[("Secondary DB: Inventory & Warehouses (SQLite)")]
        CSV_DB[("Ad-Hoc Data: Sales Reps (DuckDB In-Memory)")]
    end

    %% Audio Ingestion & Transcription
    MIC --> AUDIO_WAV --> ASR --> RAW_TRANSCRIPT
    
    %% NLP Pipeline
    RAW_TRANSCRIPT --> CORRECTOR --> CORRECTED_QUERY
    CORRECTED_QUERY --> CLARIFIER
    CLARIFIER -- "Ambiguous Intent" --> TTS
    CLARIFIER -- "Clear Intent" --> MEMORY
    MEMORY --> ROUTER
    ROUTER --> PRUNER
    
    %% Schema Profiling
    OLIST_DB -.-> PRUNER
    INV_DB -.-> PRUNER
    CSV_DB -.-> PRUNER
    
    %% SQL Generation & AST Validation
    PRUNER --> LLM_SQL --> INJ_GUARD --> AST_GUARD
    AST_GUARD -- "Violates Read-Only" --> UI
    AST_GUARD -- "Approved Read-Only SELECT" --> DataLayer
    
    %% Execution & Self-Repair Loop
    DataLayer -- "SQL Execution Error" --> LLM_REPAIR
    LLM_REPAIR -- "Corrected SQL" --> AST_GUARD
    DataLayer -- "Query Result (Pandas DataFrame)" --> LLM_INSIGHT
    
    %% Visualization & Speech Output
    LLM_INSIGHT --> TTS --> AUDIO_OUT --> UI
    DataLayer --> UI
```

---

## 2. End-to-End Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Business User
    participant UI as Streamlit Web UI
    participant STT as Local faster-whisper (Offline)
    participant NLP as Domain Corrector & Router
    participant LLM as Groq LLM (gpt-oss-120b)
    participant Sec as AST Safety Guardrail
    participant DB as Target Database Engine
    participant Analytics as Analytics & TTS Engine

    User->>UI: Speaks query into microphone
    UI->>STT: Raw audio buffer (.wav)
    Note over STT: Transcribes locally on CPU (int8)<br/>Zero audio leaves the device
    STT-->>NLP: Raw transcript (e.g., "revenue in san paulo")
    
    Note over NLP: Scans DB categorical entities<br/>Fuzzy & phonetic word replacement
    NLP-->>NLP: Corrected query ("revenue in sao paulo")
    NLP-->>NLP: Routes to optimal database ('olist')
    NLP-->>NLP: Prunes schema & injects foreign-key bridges
    
    NLP->>LLM: Dialect-specific Text-to-SQL prompt
    LLM-->>Sec: Candidate SQL query
    
    Note over Sec: sqlglot parses SQL AST tree<br/>Verifies root == SELECT<br/>Refuses DDL/DML/piggybacking
    alt Dangerous Query Detected (DROP/DELETE/ALTER)
        Sec-->>UI: Security Refusal Error (Zero DB Execution)
    else Safe SELECT Query
        Sec->>DB: Execute query
        alt Database Execution Error
            DB-->>LLM: Error traceback & original SQL
            Note over LLM: Self-Repair Loop (attempt 1-3)
            LLM->>Sec: Repaired SQL
            Sec->>DB: Re-execute repaired SQL
        end
        DB-->>Analytics: Resulting dataset (DataFrame)
        Analytics->>Analytics: Generate Plotly chart (Bar/Line/Pie)
        Analytics->>LLM: Synthesize 1-2 sentence spoken takeaway
        LLM-->>Analytics: Spoken summary text
        Analytics->>Analytics: Local pyttsx3 synthesizes audio (.wav)
        Analytics-->>UI: Render Chart, Data Table & Play Audio
        UI-->>User: Visual insights + Spoken audio playback
    end
```

---

## 3. Component Details & Privacy Guarantees

### A. 100% Offline Local Speech Processing
- **Automatic Speech Recognition (ASR):** Powered by `faster-whisper` (`base.en` model with `int8` CTranslate2 quantization). Runs strictly on the local CPU without external HTTP calls. Audio captures are converted directly in RAM to PCM 16kHz monochannel arrays.
- **Text-to-Speech (TTS):** Powered by `pyttsx3` using Windows native SAPI5 voices (David / Zira) or Linux `espeak`. Operates fully disconnected from the internet, completely eliminating voice biometric leakage and ensuring compliance with healthcare and enterprise data privacy regulations.

### B. Dynamic Zero-Config Schema Profiling & Pruning
- Rather than dumping the entire schema into the LLM context, `DatabaseProfiler` extracts table schemas, primary keys, foreign keys, row counts, and distinct sample values on startup.
- `SchemaLinker` dynamically scores tables against user query tokens, retains only the top relevant tables, and traverses the foreign key graph to inject necessary join bridging tables (e.g., connecting `customers` to `order_items` via `orders`).

### C. Phonetic Domain Word Correction
- Speech recognition models frequently mishear specialized foreign nouns, Brazilian cities, and product categories (e.g., "san paulo" for "sao paulo", "bell horizonte" for "belo horizonte", "curitibia" for "curitiba").
- `DomainWordCorrector` dynamically harvests distinct entity values across active databases and performs a two-stage alignment:
  1. Priority alias map for common dialectal phonetic variations.
  2. Multi-word n-gram fuzzy matching with Levenshtein token distance and word-boundary safety filters.

### D. Zero-Trust AST Security Guardrail
- Natural language to SQL models are vulnerable to prompt injections, destructive data modifications, and privilege escalations.
- `SafetyGuardrail` parses the generated SQL into an Abstract Syntax Tree (AST) using `sqlglot`. It enforces that:
  - The root node must be an explicit `SELECT` or `UNION`.
  - Disallowed statement nodes (`Drop`, `Delete`, `Update`, `Insert`, `Create`, `Alter`, `TruncateTable`, `Command`, `Pragma`) are rejected before touching the database connection.
  - Multi-query piggybacking (queries with semicolons followed by secondary commands) is strictly prohibited.
