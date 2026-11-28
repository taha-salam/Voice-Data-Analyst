"""
Text-to-SQL Generator Engine:
Converts natural language queries into dialect-compliant, executable SQL using Groq LLM.
Enforces guardrails and handles conversational history for follow-up questions.
"""
import re
import os
import json
import time
from typing import Dict, Any, Optional, Tuple, List
from groq import Groq
from src.config import Config
from src.nlp.guardrails import SafetyGuardrail

class SQLGenerator:
    """Generates dialect-accurate SQL from natural language questions and database schemas."""

    EMPTY_SQL_ERROR_MESSAGE = "The model did not return a query. Please try again."
    EMPTY_SQL_RETRY_INSTRUCTION = "Return only the JSON object with a non-empty sql field"
    _NON_NUMERIC_TYPES = ("char", "text", "str", "clob", "date", "time", "bool")
    _REVENUE_HINTS = ("price", "revenue", "sales", "amount", "payment", "value", "total", "income")
    _COST_HINTS = ("cost", "cogs", "expense", "wholesale", "purchase_cost")

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key)

    @classmethod
    def _extract_schema_columns(cls, schema_prompt: str) -> Tuple[List[str], List[str]]:
        """Extracts (all_column_names, numeric_metric_column_names) from a formatted schema_prompt."""
        all_cols: List[str] = []
        numeric_cols: List[str] = []
        for match in re.finditer(r"Columns:\s*(.+)", schema_prompt or ""):
            cols_str = match.group(1)
            for part in cols_str.split(","):
                part = part.strip()
                if not part:
                    continue
                col_match = re.match(r"([A-Za-z0-9_]+)\s*(?:\(([^)]*)\))?", part)
                if not col_match:
                    continue
                cname = col_match.group(1)
                ctype = (col_match.group(2) or "").lower()
                clower = cname.lower()
                all_cols.append(clower)
                if clower == "id" or clower.endswith("_id") or clower.startswith("id_"):
                    continue
                if ctype and any(tok in ctype for tok in cls._NON_NUMERIC_TYPES):
                    continue
                if cname not in numeric_cols:
                    numeric_cols.append(cname)
        return all_cols, numeric_cols

    @classmethod
    def _format_available_metrics(cls, numeric_cols: List[str]) -> str:
        """Formats closest available numeric columns into a readable suggestion list."""
        readable = [c.replace("_", " ") for c in numeric_cols[:4]]
        if not readable:
            return "the available columns in the schema"
        if len(readable) == 1:
            return readable[0]
        if len(readable) == 2:
            return f"{readable[0]} or {readable[1]}"
        return f"{', '.join(readable[:-1])}, or {readable[-1]}"

    @classmethod
    def _detect_missing_metric(cls, question: str, schema_prompt: str) -> Optional[str]:
        """
        Checks if the question asks for a metric (e.g., profit, margin, cost of goods)
        that has no matching column and cannot be computed from the profiled schema.
        """
        all_cols, numeric_cols = cls._extract_schema_columns(schema_prompt)
        if not all_cols:
            return None

        q_lower = (question or "").lower()
        has_revenue_col = any(any(h in c for h in cls._REVENUE_HINTS) for c in all_cols)
        has_cost_col = any(any(h in c for h in cls._COST_HINTS) for c in all_cols)

        missing_metric: Optional[str] = None
        if re.search(r"\b(gross\s+margin|net\s+margin|profit\s+margin|margin)\b", q_lower):
            if not any("margin" in c or "profit" in c for c in all_cols) and not (has_revenue_col and has_cost_col):
                missing_metric = "margin"
        elif re.search(r"\bprofits?\b", q_lower):
            if not any("profit" in c for c in all_cols) and not (has_revenue_col and has_cost_col):
                missing_metric = "profit"
        elif re.search(r"\b(cost\s+of\s+goods|cogs)\b", q_lower):
            if not any("cogs" in c or "cost" in c for c in all_cols):
                missing_metric = "cost of goods"
        elif re.search(r"\b(roi|return\s+on\s+investment)\b", q_lower):
            if not any("roi" in c or "investment" in c for c in all_cols):
                missing_metric = "ROI"
        elif re.search(r"\bebitda\b", q_lower):
            if not any("ebitda" in c for c in all_cols):
                missing_metric = "EBITDA"

        if not missing_metric:
            return None

        available_str = cls._format_available_metrics(numeric_cols)
        return (
            f"This database has no {missing_metric} data. "
            f"I can use {available_str} instead. Which would you like?"
        )

    def _build_completion_kwargs(
        self,
        messages: List[Dict[str, str]],
        use_json_mode: bool = True,
    ) -> Dict[str, Any]:
        """Builds Groq chat.completions.create kwargs with safe token/reasoning settings."""
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1500,
        }
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if "gpt-oss" in (self.model or "").lower():
            kwargs["reasoning_effort"] = "low"
            kwargs["include_reasoning"] = False
        return kwargs

    def _request_sql(
        self,
        messages: List[Dict[str, str]],
        schema_prompt: str = "",
    ) -> Tuple[str, str, Optional[str]]:
        """Calls the LLM and extracts (sql_query, reasoning, missing_metric_message)."""
        try:
            response = self.client.chat.completions.create(
                **self._build_completion_kwargs(messages, use_json_mode=True)
            )
            raw_content = (response.choices[0].message.content or "").strip()
            if not raw_content:
                return "", "", None
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, dict):
                    missing_metric = str(parsed.get("missing_metric") or "").strip()
                    if missing_metric:
                        reasoning = str(parsed.get("reasoning") or "").strip()
                        if not reasoning or "no " not in reasoning.lower():
                            _, numeric_cols = self._extract_schema_columns(schema_prompt)
                            avail = str(parsed.get("available_metrics") or "").strip() or self._format_available_metrics(numeric_cols)
                            reasoning = (
                                f"This database has no {missing_metric} data. "
                                f"I can use {avail} instead. Which would you like?"
                            )
                        return "", reasoning, reasoning
                    sql_query = str(parsed.get("sql") or "").strip()
                    reasoning = str(parsed.get("reasoning") or "").strip()
                    return sql_query, reasoning, None
            except json.JSONDecodeError:
                pass
            sql_match = re.search(r'```(?:sql)?(.*?)```', raw_content, re.DOTALL)
            sql_query = sql_match.group(1).strip() if sql_match else raw_content
            return sql_query, "Query generated from question.", None
        except Exception:
            # Fallback if json_object response_format is unsupported by the model
            response = self.client.chat.completions.create(
                **self._build_completion_kwargs(messages, use_json_mode=False)
            )
            raw_text = (response.choices[0].message.content or "").strip()
            if not raw_text:
                return "", "", None
            sql_match = re.search(r'```(?:sql)?(.*?)```', raw_text, re.DOTALL)
            sql_query = sql_match.group(1).strip() if sql_match else raw_text
            return sql_query, "Query generated from question.", None

    def generate_sql(
        self,
        question: str,
        schema_prompt: str,
        dialect: str = "sqlite",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generates an executable read-only SQL query for the given question and schema.
        Returns dict with 'sql', 'reasoning', 'is_safe', 'latency_seconds'.
        """
        start_time = time.perf_counter()

        # Step 1: Pre-generation intent safety check
        is_intent_safe, refusal_reason = SafetyGuardrail.check_user_intent_safety(question)
        if not is_intent_safe:
            return {
                "status": "refused",
                "sql": None,
                "reasoning": refusal_reason,
                "is_safe": False,
                "refusal": True,
                "error": None,
                "latency_seconds": round(time.perf_counter() - start_time, 3)
            }

        # Step 1.5: Check for requested metrics that do not exist and cannot be computed from the schema
        missing_metric_msg = self._detect_missing_metric(question, schema_prompt)
        if missing_metric_msg:
            return {
                "status": "error",
                "sql": None,
                "reasoning": missing_metric_msg,
                "is_safe": False,
                "refusal": False,
                "error": missing_metric_msg,
                "latency_seconds": round(time.perf_counter() - start_time, 3)
            }

        # Step 2: System prompt defining SQL generation rules
        system_instruction = f"""You are an expert Data Analyst and SQL engineer.
Your task is to write a single, read-only SQL query that accurately answers the user's question.

CRITICAL RULES:
1. DIALECT: Target SQL dialect is '{dialect.upper()}'. Use valid functions for this dialect (e.g. strftime for SQLite, date_trunc for Postgres/DuckDB).
2. SAFETY: Generate ONLY read-only SELECT queries. NEVER generate DROP, DELETE, UPDATE, INSERT, ALTER, or PRAGMA statements.
3. LIMITS: When the question asks for 'top' or 'best' without a specific number (e.g. 'top customers', 'top products'), limit results to 10 (LIMIT 10). Always add 'LIMIT 100' for general unaggregated queries unless the user specifies otherwise or uses GROUP BY.
4. METRICS / 'BOTH': If the user asks for 'both' metrics (e.g., spend and order count), include both aggregations in the SELECT clause (e.g., SUM(payment_value) AS total_spend, COUNT(DISTINCT order_id) AS total_orders) and ORDER BY the primary one DESC.
5. METRIC DEFINITION: "revenue" and "sales" mean the sum of the item price (or the payment amount) only. Do not add shipping, freight, tax, discounts, or fees unless the user explicitly asks for them (for example "including shipping").
6. SCHEMA: Use ONLY the tables and column names provided in the schema below. Do not invent columns.
7. JOINS: Join tables using the foreign-key relationships specified in the schema.
8. MISSING METRICS: If the question asks for a metric that does NOT exist in the provided schema and CANNOT be computed from the available columns (for example: profit, margin, cost of goods, or any metric with no matching or component columns), DO NOT substitute a different unrelated column. Instead, return valid JSON with:
   - "sql": ""
   - "missing_metric": "<the missing metric name>"
   - "available_metrics": "<closest available numeric metrics from the schema>"
   - "reasoning": "This database has no <metric> data. I can use <closest available metrics> instead. Which would you like?"
9. OUTPUT FORMAT: Return your response strictly as valid JSON with two fields (plus optional missing_metric/available_metrics when rule 8 applies):
   - "sql": "The clean SQL query string without markdown fences"
   - "reasoning": "Brief 1-sentence explanation of how the query computes the result"

AVAILABLE SCHEMA:
{schema_prompt}
"""

        messages = [{"role": "system", "content": system_instruction}]

        # Inject previous conversation history if available (for follow-ups)
        if conversation_history:
            for turn in conversation_history[-4:]:
                messages.append(turn)

        messages.append({
            "role": "user",
            "content": f"User Question: {question}"
        })

        try:
            sql_query, reasoning, llm_missing_msg = self._request_sql(messages, schema_prompt=schema_prompt)
            if llm_missing_msg:
                return {
                    "status": "error",
                    "sql": None,
                    "reasoning": llm_missing_msg,
                    "is_safe": False,
                    "refusal": False,
                    "error": llm_missing_msg,
                    "latency_seconds": round(time.perf_counter() - start_time, 3)
                }
            if not sql_query or not sql_query.strip():
                retry_messages = messages + [{
                    "role": "user",
                    "content": self.EMPTY_SQL_RETRY_INSTRUCTION
                }]
                sql_query, reasoning, llm_missing_msg = self._request_sql(retry_messages, schema_prompt=schema_prompt)
                if llm_missing_msg:
                    return {
                        "status": "error",
                        "sql": None,
                        "reasoning": llm_missing_msg,
                        "is_safe": False,
                        "refusal": False,
                        "error": llm_missing_msg,
                        "latency_seconds": round(time.perf_counter() - start_time, 3)
                    }
        except Exception as inner_e:
            err_msg = str(inner_e)
            if "model_not_found" in err_msg or "404" in err_msg:
                err_msg = f"Groq Model Not Found (404) for '{self.model}'. Please verify GROQ_MODEL in your .env (recommended: openai/gpt-oss-120b or llama-3.3-70b-versatile)."
            return {
                "status": "error",
                "sql": None,
                "reasoning": f"LLM Generation Error: {err_msg}",
                "is_safe": False,
                "refusal": False,
                "error": err_msg,
                "latency_seconds": round(time.perf_counter() - start_time, 3)
            }

        if not sql_query or not sql_query.strip():
            return {
                "status": "error",
                "sql": None,
                "reasoning": self.EMPTY_SQL_ERROR_MESSAGE,
                "is_safe": False,
                "refusal": False,
                "error": self.EMPTY_SQL_ERROR_MESSAGE,
                "latency_seconds": round(time.perf_counter() - start_time, 3)
            }

        # Step 3: Post-generation AST safety validation
        is_sql_safe, sql_error = SafetyGuardrail.validate_sql(sql_query, dialect=dialect)
        latency = time.perf_counter() - start_time

        if not is_sql_safe:
            return {
                "status": "refused",
                "sql": sql_query,
                "reasoning": f"Security Refusal: {sql_error}",
                "is_safe": False,
                "refusal": True,
                "error": None,
                "latency_seconds": round(latency, 3)
            }

        return {
            "status": "ok",
            "sql": sql_query,
            "reasoning": reasoning,
            "is_safe": True,
            "refusal": False,
            "error": None,
            "latency_seconds": round(latency, 3)
        }
