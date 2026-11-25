"""
Spoken Clarification Engine:
Detects vague or underspecified business questions (e.g., 'show me top customers')
and generates concise spoken clarifying questions with actionable choices instead of guessing.
"""
import re
import json
from typing import Dict, Any, Tuple, Optional, List
from groq import Groq
from src.config import Config

class ClarificationEngine:
    """Detects query ambiguity and generates short spoken clarifying questions."""

    # Common ambiguous patterns in business analytics queries
    AMBIGUITY_PATTERNS = [
        # "top customers" without metric
        (re.compile(r'\btop\s+customers?\b', re.IGNORECASE),
         r'by\s+(revenue|sales|spend|spending|orders|count|purchases)',
         "Would you like top customers ranked by total spend or by total number of orders?"),
        
        # "top products" or "best products" without metric
        (re.compile(r'\b(top|best|popular)\s+products?\b', re.IGNORECASE),
         r'by\s+(revenue|sales|volume|quantity|units|reviews|rating)',
         "Would you like top products ranked by total revenue or by units sold?"),
         
        # "top sellers" without metric
        (re.compile(r'\b(top|best)\s+sellers?\b', re.IGNORECASE),
         r'by\s+(revenue|sales|orders|volume)',
         "Would you like top sellers ranked by total sales revenue or by completed orders?"),

        # "show orders" or "show sales" without time or filter
        (re.compile(r'^\s*(show|list|get)\s+(me\s+)?(all\s+)?(orders|sales)\s*$', re.IGNORECASE),
         r'',
         "Would you like to see recent orders, orders broken down by month, or orders filtered by city?")
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key)

    def evaluate_ambiguity(self, question: str) -> Dict[str, Any]:
        """
        Determines whether a question needs clarification before generating SQL.
        Returns dict with 'needs_clarification', 'clarification_prompt', and 'options'.
        """
        q_clean = question.strip()

        # 1. Fast heuristic pattern check
        for trigger_pat, qualifier_pat, question_text in self.AMBIGUITY_PATTERNS:
            if trigger_pat.search(q_clean):
                if not qualifier_pat or not re.search(qualifier_pat, q_clean, re.IGNORECASE):
                    return {
                        "needs_clarification": True,
                        "clarification_prompt": question_text,
                        "type": "heuristic"
                    }

        # 2. LLM-based ambiguity check for open-ended queries (< 5 words with vague intent)
        words = q_clean.split()
        if len(words) <= 4 and not any(k in q_clean.lower() for k in ["how many", "count", "average", "avg", "total", "sum", "who is", "list"]):
            return self._llm_check_ambiguity(q_clean)

        return {
            "needs_clarification": False,
            "clarification_prompt": None,
            "type": "unambiguous"
        }

    def _llm_check_ambiguity(self, question: str) -> Dict[str, Any]:
        """Uses LLM to check if brief query has multiple conflicting interpretations."""
        prompt = f"""Analyze if this business question is too vague to write an exact SQL query without guessing:
Question: "{question}"

If vague, formulate a short, polite 1-sentence spoken question asking the user to choose their preferred metric.
Return strictly JSON:
{{
  "is_vague": true/false,
  "clarifying_question": "Short spoken question or null"
}}"""
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            if data.get("is_vague"):
                return {
                    "needs_clarification": True,
                    "clarification_prompt": data.get("clarifying_question"),
                    "type": "llm"
                }
        except Exception:
            pass

        return {
            "needs_clarification": False,
            "clarification_prompt": None,
            "type": "default"
        }

    @staticmethod
    def resolve_clarification(original_question: str, user_answer: str) -> str:
        """Merges the user's spoken clarification with the original question."""
        orig = original_question.strip().rstrip("?.")
        ans = user_answer.strip().lower()
        
        # If user answer starts with "by", append directly
        if ans.startswith("by "):
            return f"{orig} {ans}"
        else:
            return f"{orig} by {ans}"
