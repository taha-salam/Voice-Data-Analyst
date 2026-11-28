"""
Conversational Memory & Voice Follow-ups Engine:
Retains conversational state across queries and intelligently modifies previous SQL queries
when users ask follow-up questions (e.g., 'now break it down by month', 'same for last year').
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from groq import Groq
from src.config import Config
from src.nlp.guardrails import SafetyGuardrail

class ConversationTurn:
    def __init__(self, question: str, sql: str, source_name: str, row_count: int = 0):
        self.question = question
        self.sql = sql
        self.source_name = source_name
        self.row_count = row_count

class ConversationMemory:
    """Maintains conversational context and handles multi-turn query refinement."""

    FOLLOWUP_REFERENCE_WORDS = {
        "now", "also", "same", "instead", "again",
        "that", "those", "them", "it", "previous",
    }

    FOLLOWUP_PATTERNS = [
        re.compile(r'\b(now\s+)?break\s+(it\s+)?down\s+by\b', re.IGNORECASE),
        re.compile(r'\b(now\s+)?group\s+by\b', re.IGNORECASE),
        re.compile(r'\blast\s+one\b', re.IGNORECASE),
        re.compile(r'\bsame\s+for\b', re.IGNORECASE),
        re.compile(r'\bwhat\s+about\b', re.IGNORECASE),
        re.compile(r'\bhow\s+about\b', re.IGNORECASE),
        re.compile(r'\bfor\s+last\s+(year|month|quarter|week)\b', re.IGNORECASE),
        re.compile(r'^\s*(and\s+)?by\s+(month|quarter|year|week|day)\b', re.IGNORECASE),
        re.compile(r'^\s*and\s+for\b', re.IGNORECASE),
        re.compile(r'^\s*only\s+(in|for)\b', re.IGNORECASE),
        re.compile(r'\bfilter\s+(by|for)\b', re.IGNORECASE),
        re.compile(r'\binstead\s+of\b', re.IGNORECASE),
        re.compile(r'\bsort\s+by\b', re.IGNORECASE),
        re.compile(r'^\s*(show|give\s+me)?\s*(only\s+)?top\s+\d+\s*$', re.IGNORECASE),
    ]

    STANDALONE_METRIC_WORDS = {
        "revenue", "sales", "spend", "spent", "spending", "total", "sum",
        "count", "average", "avg", "mean", "price", "cost", "profit",
        "tip", "tips", "orders", "quantity", "qty", "rate", "ratio",
        "score", "commission", "quota", "stock", "inventory", "income",
    }

    ELLIPTICAL_LEADING_WORDS = {"and", "or", "by", "for", "in", "only", "with", "just"}

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.turns: List[ConversationTurn] = []
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key)

    def add_turn(self, question: str, sql: str, source_name: str, row_count: int = 0):
        """Records a successful turn in conversation history."""
        self.turns.append(ConversationTurn(question, sql, source_name, row_count))

    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Returns the most recent conversation turn if available."""
        return self.turns[-1] if self.turns else None

    def is_followup(self, question: str, current_source: Optional[str] = None) -> bool:
        """
        Determines if the question clearly refers back to the previous turn.
        Standalone questions with their own metric and dimension, or questions routed
        to a different data source than the previous turn, are not treated as follow-ups.
        """
        if not self.turns:
            return False

        last_turn = self.turns[-1]
        if current_source and last_turn.source_name and current_source != last_turn.source_name:
            return False

        q_clean = re.sub(r"[?!.,;]+$", "", (question or "").strip()).strip()
        if not q_clean:
            return False

        q_lower = q_clean.lower()
        words = re.findall(r"\b[a-z0-9_']+\b", q_lower)
        if not words:
            return False
        word_set = set(words)

        # 1. Explicit back-reference words (now, also, same, instead, again, that, those, them, it, previous)
        if word_set & self.FOLLOWUP_REFERENCE_WORDS:
            return True

        # 2. Explicit follow-up phrases ("break it down", "last one", "for last year", leading "by month", etc.)
        for pattern in self.FOLLOWUP_PATTERNS:
            if pattern.search(q_lower):
                return True

        # 3. Very short elliptical fragment with no subject/metric of its own (e.g. "in 2023", "by region", "for credit card")
        has_metric = bool(word_set & self.STANDALONE_METRIC_WORDS)
        if len(words) <= 4 and words[0] in self.ELLIPTICAL_LEADING_WORDS and not has_metric:
            return True

        return False

    def generate_followup_sql(
        self,
        followup_question: str,
        schema_prompt: str,
        dialect: str = "sqlite"
    ) -> Dict[str, Any]:
        """
        Modifies the previous query according to the follow-up request rather than restarting from scratch.
        """
        last_turn = self.get_last_turn()
        if not last_turn:
            raise ValueError("No previous conversation turn available for follow-up.")

        prompt = f"""You are modifying an existing SQL query in '{dialect.upper()}' dialect based on a user follow-up instruction.

PREVIOUS USER QUESTION:
"{last_turn.question}"

PREVIOUS SQL QUERY:
{last_turn.sql}

FOLLOW-UP INSTRUCTION:
"{followup_question}"

AVAILABLE DATABASE SCHEMA:
{schema_prompt}

INSTRUCTIONS:
1. Modify the previous SQL query to satisfy the follow-up request (e.g. adjust WHERE clause, add GROUP BY, change time filter, or modify ORDER BY).
2. DO NOT start from scratch if the base calculation remains the same.
3. METRIC DEFINITION: "revenue" and "sales" mean the sum of the item price (or the payment amount) only. Do not add shipping, freight, tax, discounts, or fees unless the user explicitly asks for them (for example "including shipping").
4. Keep the query strictly read-only SELECT.
5. Output format: Return strictly JSON with keys "sql" and "reasoning".
"""

        create_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 1500,
        }
        if "gpt-oss" in (self.model or "").lower():
            create_kwargs["reasoning_effort"] = "low"
            create_kwargs["include_reasoning"] = False

        try:
            res = self.client.chat.completions.create(
                **create_kwargs,
                response_format={"type": "json_object"}
            )
            raw_content = (res.choices[0].message.content or "").strip()
            sql, reasoning = self._extract_sql_and_reasoning(raw_content)
        except Exception:
            try:
                # Fallback direct generation
                res = self.client.chat.completions.create(**create_kwargs)
                raw_content = (res.choices[0].message.content or "").strip()
                sql, reasoning = self._extract_sql_and_reasoning(raw_content)
            except Exception as exc:
                err_msg = str(exc)
                if "model_not_found" in err_msg or "404" in err_msg:
                    err_msg = f"Groq Model Not Found (404) for '{self.model}'. Please check GROQ_MODEL in your .env."
                return {
                    "status": "error",
                    "sql": None,
                    "reasoning": f"LLM Generation Error: {err_msg}",
                    "is_safe": False,
                    "is_followup": True,
                    "refusal": False,
                    "error": err_msg,
                    "previous_sql": last_turn.sql
                }

        # Safety validation
        is_safe, error = SafetyGuardrail.validate_sql(sql, dialect=dialect)
        return {
            "status": "ok" if is_safe else "refused",
            "sql": sql,
            "reasoning": reasoning or "Query modified based on follow-up.",
            "is_safe": is_safe,
            "is_followup": True,
            "refusal": not is_safe,
            "error": error if not is_safe else None,
            "previous_sql": last_turn.sql
        }

    @staticmethod
    def _extract_sql_and_reasoning(raw_text: str) -> Tuple[str, str]:
        """Extracts SQL and reasoning cleanly whether JSON, markdown, or raw text is returned."""
        # 1. Try JSON parsing
        try:
            data = json.loads(raw_text)
            sql = data.get("sql", "").strip()
            reasoning = data.get("reasoning", "")
            sql = re.sub(r'^```(?:sql)?\s*', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\s*```$', '', sql).strip()
            if sql:
                return sql, reasoning
        except Exception:
            pass

        # 2. Try regex extraction of "sql": "..."
        json_sql_match = re.search(r'"sql"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text)
        if json_sql_match:
            try:
                parsed_sql = json_sql_match.group(1).encode('utf-8').decode('unicode_escape')
                return parsed_sql.strip(), "Extracted from response."
            except Exception:
                return json_sql_match.group(1).strip(), "Extracted from response."

        # 3. Try markdown block
        match = re.search(r'```(?:sql)?(.*?)```', raw_text, re.DOTALL)
        if match:
            return match.group(1).strip(), "Extracted from code block."

        # 4. Try finding SELECT statement
        match_select = re.search(r'\b(SELECT\s+.*)', raw_text, re.DOTALL | re.IGNORECASE)
        if match_select:
            clean_stmt = match_select.group(1).split(';')[0] + ';'
            return clean_stmt.strip(), "Extracted statement."

        return raw_text.strip(), ""
