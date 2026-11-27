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

    FOLLOWUP_PATTERNS = [
        re.compile(r'\b(now\s+)?break\s+(it\s+)?down\s+by\b', re.IGNORECASE),
        re.compile(r'\b(now\s+)?group\s+by\b', re.IGNORECASE),
        re.compile(r'\bsame\s+for\b', re.IGNORECASE),
        re.compile(r'\bwhat\s+about\b', re.IGNORECASE),
        re.compile(r'\band\s+for\b', re.IGNORECASE),
        re.compile(r'\bonly\s+(in|for)\b', re.IGNORECASE),
        re.compile(r'\bfilter\s+(by|for)\b', re.IGNORECASE),
        re.compile(r'\binstead\s+of\b', re.IGNORECASE),
        re.compile(r'\bsort\s+by\b', re.IGNORECASE),
        re.compile(r'\b(show|give\s+me)\s+(only\s+)?top\s+\d+\b', re.IGNORECASE)
    ]

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

    def is_followup(self, question: str) -> bool:
        """Determines if the question is an iterative modification of the previous query."""
        if not self.turns:
            return False

        q_lower = question.strip().lower()
        
        # Check explicit followup patterns
        for pattern in self.FOLLOWUP_PATTERNS:
            if pattern.search(q_lower):
                return True

        # Short elliptical questions like "and in 2023?" or "by category?"
        words = q_lower.split()
        if len(words) <= 5 and any(w in words for w in ["and", "or", "by", "for", "with", "only", "month", "quarter"]):
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
3. Keep the query strictly read-only SELECT.
4. Output format: Return strictly JSON with keys "sql" and "reasoning".
"""

        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            raw_content = res.choices[0].message.content.strip()
            sql, reasoning = self._extract_sql_and_reasoning(raw_content)
        except Exception:
            try:
                # Fallback direct generation
                res = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=1000
                )
                raw_content = res.choices[0].message.content.strip()
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
