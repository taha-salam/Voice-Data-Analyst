"""
Spoken Clarification Engine:
Detects vague or underspecified business questions (e.g., 'show me top customers')
and generates concise spoken clarifying questions with actionable choices instead of guessing.
"""
import re
import json
from typing import Dict, Any, Tuple, Optional, List
from rapidfuzz import fuzz
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
        Uses regex patterns, typo-tolerant fuzzy matching (rapidfuzz), and LLM fallback.
        Returns dict with 'needs_clarification', 'clarification_prompt', and 'type'.
        """
        q_clean = question.strip()
        q_lower = q_clean.lower()
        words = re.findall(r'\b\w+\b', q_lower)

        # 1. Fast regex heuristic pattern check
        for trigger_pat, qualifier_pat, question_text in self.AMBIGUITY_PATTERNS:
            if trigger_pat.search(q_clean):
                if not qualifier_pat or not re.search(qualifier_pat, q_clean, re.IGNORECASE):
                    return {
                        "needs_clarification": True,
                        "clarification_prompt": question_text,
                        "type": "heuristic"
                    }

        # 2. Typo-tolerant fuzzy matching for "top/best" queries (e.g. "top cutomers", "best customrs")
        has_ranking_intent = any(w in words for w in ["top", "best", "popular", "leading"]) or any(
            fuzz.ratio(w, "top") >= 85 or fuzz.ratio(w, "best") >= 85 for w in words
        )
        if has_ranking_intent:
            # Check for customers entity with typo tolerance
            has_customers = any(fuzz.ratio(w, "customers") >= 80 or fuzz.ratio(w, "customer") >= 80 for w in words)
            has_customer_metric = bool(re.search(r'by\s+(revenue|sales|spend|spending|orders|count|purchases)', q_lower))
            if has_customers and not has_customer_metric:
                return {
                    "needs_clarification": True,
                    "clarification_prompt": "Would you like top customers ranked by total spend or by total number of orders?",
                    "type": "fuzzy_heuristic"
                }

            # Check for products entity with typo tolerance
            has_products = any(fuzz.ratio(w, "products") >= 80 or fuzz.ratio(w, "product") >= 80 for w in words)
            has_product_metric = bool(re.search(r'by\s+(revenue|sales|volume|quantity|units|reviews|rating)', q_lower))
            if has_products and not has_product_metric:
                return {
                    "needs_clarification": True,
                    "clarification_prompt": "Would you like top products ranked by total revenue or by units sold?",
                    "type": "fuzzy_heuristic"
                }

            # Check for sellers entity with typo tolerance
            has_sellers = any(fuzz.ratio(w, "sellers") >= 80 or fuzz.ratio(w, "seller") >= 80 for w in words)
            has_seller_metric = bool(re.search(r'by\s+(revenue|sales|orders|volume)', q_lower))
            if has_sellers and not has_seller_metric:
                return {
                    "needs_clarification": True,
                    "clarification_prompt": "Would you like top sellers ranked by total sales revenue or by completed orders?",
                    "type": "fuzzy_heuristic"
                }

        # 3. LLM-based ambiguity check for brief open-ended queries (<= 7 words with vague intent)
        if len(words) <= 7 and not any(k in q_lower for k in ["how many", "count", "average", "avg", "total", "sum", "who is", "list"]):
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
        """
        Merges the user's spoken clarification with the original question into a clean,
        grammatical analytical query, enforcing default limit 10 for 'top' queries.
        """
        orig = original_question.strip().rstrip("?.")
        ans = user_answer.strip().lower()

        # Clean conversational filler phrases from user speech
        clean_ans = ans
        fillers = [
            "give me", "i want", "i would like", "can you show", "show me", "please",
            "ranked by", "rank by", "filter by", "by", "what about", "how about"
        ]
        for filler in fillers:
            if clean_ans.startswith(filler + " "):
                clean_ans = clean_ans[len(filler):].strip()
            elif clean_ans.endswith(" " + filler):
                clean_ans = clean_ans[:-len(filler)].strip()

        # Handle 'both' (e.g. "both", "give me both", "both spend and orders")
        if "both" in ans:
            metric_clause = "total spend and total number of orders"
        elif any(k in clean_ans for k in ["spend", "spending", "revenue", "money", "sales", "dollar", "amount"]):
            metric_clause = "total spend"
        elif any(k in clean_ans for k in ["order", "orders", "count", "volume", "number of orders", "units", "quantity"]):
            metric_clause = "total number of orders"
        else:
            metric_clause = clean_ans or ans

        # Normalize "top" without a number to "top 10" (e.g., "top customers" -> "top 10 customers")
        orig_normalized = re.sub(r'\btop\s+(?!(\d+))\b', 'top 10 ', orig, flags=re.IGNORECASE)
        orig_normalized = re.sub(r'\bbest\s+(?!(\d+))\b', 'top 10 ', orig_normalized, flags=re.IGNORECASE)

        return f"{orig_normalized} ranked by {metric_clause}"
