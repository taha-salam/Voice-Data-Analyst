"""
Self-Repair Loop for SQL Execution:
Intercepts runtime SQL syntax errors or execution failures, prompts the LLM with the error trace,
and iterates to fix the query up to a strict retry limit (max 3 retries).
"""
import time
import json
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from groq import Groq
from src.config import Config
from src.nlp.guardrails import SafetyGuardrail

class SelfRepairEngine:
    """Handles automatic query correction when database execution fails."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, max_retries: int = 3):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.max_retries = max_retries
        self.client = Groq(api_key=self.api_key)

    def execute_with_repair(
        self,
        db_source,
        initial_sql: str,
        user_question: str,
        schema_prompt: str,
        dialect: str = "sqlite"
    ) -> Dict[str, Any]:
        """
        Executes SQL query on db_source. If an error occurs, feeds the error trace back to the LLM
        and retries execution up to max_retries.
        """
        current_sql = initial_sql
        repair_history: List[Dict[str, Any]] = []
        start_time = time.perf_counter()

        for attempt in range(1, self.max_retries + 1):
            try:
                # Validate guardrails before every execution attempt
                is_safe, refusal_reason = SafetyGuardrail.validate_sql(current_sql, dialect=dialect)
                if not is_safe:
                    return {
                        "success": False,
                        "df": pd.DataFrame(),
                        "final_sql": current_sql,
                        "error": refusal_reason,
                        "repair_history": repair_history,
                        "attempts": attempt,
                        "latency_seconds": round(time.perf_counter() - start_time, 3)
                    }

                # Attempt execution
                df, exec_time = db_source.execute_query(current_sql)
                
                return {
                    "success": True,
                    "df": df,
                    "final_sql": current_sql,
                    "error": None,
                    "repair_history": repair_history,
                    "attempts": attempt,
                    "latency_seconds": round(time.perf_counter() - start_time, 3)
                }

            except Exception as e:
                error_msg = str(e)
                repair_entry = {
                    "attempt": attempt,
                    "failed_sql": current_sql,
                    "error": error_msg
                }

                if attempt >= self.max_retries:
                    repair_history.append(repair_entry)
                    break

                # Request fix from LLM
                repaired_sql = self._request_query_fix(
                    failed_sql=current_sql,
                    error_message=error_msg,
                    user_question=user_question,
                    schema_prompt=schema_prompt,
                    dialect=dialect
                )

                repair_entry["repaired_sql"] = repaired_sql
                repair_history.append(repair_entry)
                current_sql = repaired_sql

        # If all retries exhausted
        return {
            "success": False,
            "df": pd.DataFrame(),
            "final_sql": current_sql,
            "error": f"Execution failed after {self.max_retries} attempts. Last error: {repair_history[-1]['error'] if repair_history else 'Unknown error'}",
            "repair_history": repair_history,
            "attempts": self.max_retries,
            "latency_seconds": round(time.perf_counter() - start_time, 3)
        }

    def _request_query_fix(
        self,
        failed_sql: str,
        error_message: str,
        user_question: str,
        schema_prompt: str,
        dialect: str
    ) -> str:
        """Prompts the LLM to analyze the error message and repair the SQL query."""
        prompt = f"""The following SQL query was generated for dialect '{dialect.upper()}' to answer:
User Question: "{user_question}"

FAILED SQL QUERY:
{failed_sql}

DATABASE ERROR MESSAGE:
{error_message}

AVAILABLE DATABASE SCHEMA:
{schema_prompt}

Please fix the SQL query to resolve the exact error. 
RULES:
1. Return ONLY the corrected SQL query.
2. Must be a valid read-only SELECT statement.
3. Use only existing columns and tables from the schema.
4. Output format: Return JSON with key "repaired_sql".
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            return parsed.get("repaired_sql", failed_sql).strip()
        except Exception:
            # Fallback regex extraction if json fails
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=500
                )
                text = response.choices[0].message.content.strip()
                import re
                match = re.search(r'```(?:sql)?(.*?)```', text, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return text.strip()
            except Exception:
                return failed_sql
