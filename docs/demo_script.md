# Voice Data Analyst — 2 to 3 Minute Loom Video Demo Script

**Project Title:** Voice Data Analyst (Conversational Multi-Source Database BI)  
**Presenter:** Taha Salam  
**Target Duration:** ~2:45 minutes  
**Format:** Screen Recording with Voiceover (Streamlit UI + Terminal verification)

---

## Pre-Recording Checklist
1. Open terminal and run the Streamlit app:
   ```powershell
   .\.venv\Scripts\streamlit.exe run app.py
   ```
2. Ensure browser is open to `http://localhost:8501` in wide mode.
3. Microphone permissions granted in browser for Streamlit `st.audio_input`.
4. Audio output enabled so local `pyttsx3` speech playback is captured in the recording.

---

## Timestamped Walkthrough & Script

### Scene 1: Introduction & System Architecture (0:00 – 0:30)
- **Visual:** Display Streamlit application header and the sidebar showing connected databases (`olist`, `inventory`, `sales_csv`) and architecture badges (`100% Offline ASR`, `100% Offline TTS`, `AST SQL Safe`).
- **Speaker:**
  > "Hello everyone! Welcome to my demonstration of the Voice Data Analyst — an intelligent business intelligence system that lets business managers query complex relational databases using natural spoken English.
  >
  > A crucial privacy requirement of this project is that **zero voice audio leaves the local machine**. Our speech recognition is powered by a local, quantized `faster-whisper` model on CPU, and our spoken responses are synthesized entirely offline using `pyttsx3`.
  >
  > Let's test the entire pipeline live."

---

### Scene 2: Live Voice Query & Phonetic Domain Correction (0:30 – 1:05)
- **Action:** Click the microphone button in Streamlit and speak:
  > *"What is the total revenue in san paulo?"* (deliberately pronouncing "san paulo" instead of "sao paulo").
- **Visual:** Streamlit displays:
  - Audio waveform captured.
  - Transcript: `"what is the total revenue in san paulo"`
  - **Blue Domain Correction Callout:** *Phonetic Correction: 'san paulo' → 'sao paulo' (Confidence: 100%)*
  - **Target Database Routed:** `olist` (Brazilian E-Commerce)
  - Generated SQL:
    ```sql
    SELECT sum(payment_value) AS total_revenue 
    FROM order_payments op 
    JOIN orders o ON op.order_id = o.order_id 
    JOIN customers c ON o.customer_id = c.customer_id 
    WHERE c.customer_city = 'sao paulo'
    ```
  - Data table and total revenue card rendered.
  - **Audio Player plays spoken insight:** *"The total revenue in São Paulo is $18,450 across the selected records."*
- **Speaker:**
  > "Notice what just happened. The speech engine transcribed 'san paulo', which doesn't match the database directly. Our Dynamic Domain Corrector intercepted the transcript, aligned it against the harvested city entities, and corrected it to 'sao paulo' before generating SQL.
  > The system pruned the schema, performed a 3-table join across customers, orders, and payments, executed the query in 5 milliseconds, and generated an executive voice summary."

---

### Scene 3: Multi-Source Database Routing & Rich Visualization (1:05 – 1:35)
- **Action:** Click microphone and speak:
  > *"What are the top five product categories by total sales volume?"*
- **Visual:** Streamlit renders:
  - Generated SQL grouping by category and ordering by count/sales descending with `LIMIT 5`.
  - **Plotly Bar Chart** showing category distribution.
  - Audio playback summarizing the peak category (e.g. `beleza_saude` or `cama_mesa_banho`).
- **Speaker:**
  > "Here, the engine automatically recognized a categorical comparison, selected an interactive Plotly horizontal bar chart, and generated an audio executive summary highlighting the leading category without reading the entire raw table."

---

### Scene 4: Multi-Turn Conversational Memory & Voice Follow-Up (1:35 – 2:00)
- **Action:** Click microphone and speak a follow-up query:
  > *"Now break it down by payment type."*
- **Visual:** Streamlit displays:
  - Context banner: *Following up on previous query: 'top 5 product categories'*.
  - Refined SQL: Adds join with `order_payments` and groups by both category and `payment_type`.
  - Updated visualization and spoken audio playback.
- **Speaker:**
  > "Notice the conversational memory in action. The user didn't have to repeat the entire question. The system recognized the linguistic follow-up cue 'break it down by', inherited the context of the previous query, and modified the SQL structure seamlessly."

---

### Scene 5: Security Guardrail & SQL Injection Refusal (2:00 – 2:25)
- **Action:** In the text input or microphone, submit an adversarial attack:
  > *"Show me all customer names; DROP TABLE customers;"*
- **Visual:**
  - Red Security Warning Banner appears:
  - **Status: BLOCKED**
  - **Reason:** `Security Refusal: Dangerous query refused: Multiple stacked queries (piggybacking) are not allowed. Destructive SQL keyword detected.`
  - Zero database execution occurs; data integrity is 100% protected.
- **Speaker:**
  > "Now let's examine security. If an attacker or compromised prompt attempts a multi-statement injection or destructive command like `DROP TABLE`, our zero-trust Abstract Syntax Tree guardrail powered by `sqlglot` parses the SQL AST before execution. It strictly requires the root node to be a read-only `SELECT` and immediately terminates malicious commands with zero impact on the database."

---

### Scene 6: Automated Test Suite & Conclusion (2:25 – 2:45)
- **Visual:** Briefly show the terminal executing the full automated test suite:
  ```powershell
  pytest -v
  ```
  Highlighting **27 passed in 42s**, including the 100% security defense rate and 50.7% WER reduction.
- **Speaker:**
  > "All components are backed by a comprehensive regression and empirical evaluation suite of 27 automated tests. In our benchmarks, the domain corrector achieved a 50.7% relative reduction in Word Error Rate, and our security guardrails achieved a 100% attack blockage rate with an end-to-end turnaround latency under 2.8 seconds.
  >
  > Thank you for watching!"
