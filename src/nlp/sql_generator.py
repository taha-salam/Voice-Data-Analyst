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

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key)

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
                "sql": None,
                "reasoning": refusal_reason,
                "is_safe": False,
                "refusal": True,
                "latency_seconds": round(time.perf_counter() - start_time, 3)
            }

        # Step 2: System prompt defining SQL generation rules
        system_instruction = f"""You are an expert Data Analyst and SQL engineer.
Your task is to write a single, read-only SQL query that accurately answers the user's question.

CRITICAL RULES:
1. DIALECT: Target SQL dialect is '{dialect.upper()}'. Use valid functions for this dialect (e.g. strftime for SQLite, date_trunc for Postgres/DuckDB).
2. SAFETY: Generate ONLY read-only SELECT queries. NEVER generate DROP, DELETE, UPDATE, INSERT, ALTER, or PRAGMA statements.
3. LIMITS: Always add 'LIMIT 100' unless the user asks for a specific limit or an aggregation with GROUP BY.
4. SCHEMA: Use ONLY the tables and column names provided in the schema below. Do not invent columns.
5. JOINS: Join tables using the foreign-key relationships specified in the schema.
6. OUTPUT FORMAT: Return your response strictly as valid JSON with two fields:
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content.strip()
            parsed = json.loads(raw_content)
            sql_query = parsed.get("sql", "").strip()
            reasoning = parsed.get("reasoning", "")
        except Exception as e:
            # Fallback if json mode isn't supported or fails
            try:
                # Retry with standard text prompt
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=600
                )
                raw_text = response.choices[0].message.content.strip()
                sql_match = re.search(r'```(?:sql)?(.*?)```', raw_text, re.DOTALL)
                if sql_match:
                    sql_query = sql_match.group(1).strip()
                else:
                    sql_query = raw_text.strip()
                reasoning = "Query generated from question."
            except Exception as inner_e:
                return {
                    "sql": None,
                    "reasoning": f"LLM Generation Error: {inner_e}",
                    "is_safe": False,
                    "refusal": False,
                    "latency_seconds": round(time.perf_counter() - start_time, 3)
                }

        # Step 3: Post-generation AST safety validation
        is_sql_safe, sql_error = SafetyGuardrail.validate_sql(sql_query, dialect=dialect)
        latency = time.perf_counter() - start_time

        if not is_sql_safe:
            return {
                "sql": sql_query,
                "reasoning": f"Security Refusal: {sql_error}",
                "is_safe": False,
                "refusal": True,
                "latency_seconds": round(latency, 3)
            }

        return {
            "sql": sql_query,
            "reasoning": reasoning,
            "is_safe": True,
            "refusal": False,
            "latency_seconds": round(latency, 3)
        }
