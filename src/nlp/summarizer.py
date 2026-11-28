"""
Analytics & Insight Engine:
1. Recommends the optimal visualization (Bar, Line, Pie, Scatter, Table) based on query output shape and types.
2. Generates punchy, spoken-friendly statistical summaries for listening (e.g., 'sales peaked in March, about 20% above average') without reading the table aloud.
"""
import re
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from groq import Groq
from src.config import Config

class AnalyticsEngine:
    """Generates chart specifications and audio-friendly spoken summaries from query results."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key)

    @staticmethod
    def recommend_visualization(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Inspects DataFrame dimensions and column types to choose the best visualization.
        Returns chart type, axis mappings, and whether a chart is suitable alongside the table.
        """
        if df.empty or len(df.columns) == 0:
            return {"chart_type": "none", "show_chart": False, "reason": "Empty dataset"}

        # Single scalar value (1 row, 1 col)
        if len(df) == 1 and len(df.columns) == 1:
            val = df.iloc[0, 0]
            col_name = df.columns[0]
            return {
                "chart_type": "metric",
                "show_chart": False,
                "metric_label": col_name.replace("_", " ").title(),
                "metric_value": str(val)
            }

        # Identify column data types
        cols = df.columns.tolist()
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        non_num_cols = [c for c in cols if c not in num_cols]
        
        # Check for time/date columns
        date_keywords = ["month", "year", "date", "timestamp", "day", "week", "quarter", "mth", "dt"]
        time_cols = [c for c in cols if any(k in c.lower() for k in date_keywords)]

        # Case 1: Time Series -> Line Chart
        if time_cols and num_cols:
            t_col = time_cols[0]
            val_col = num_cols[0]
            return {
                "chart_type": "line",
                "show_chart": True,
                "x": t_col,
                "y": val_col,
                "title": f"{val_col.replace('_', ' ').title()} over {t_col.replace('_', ' ').title()}"
            }

        # Case 2: Categorical + Numerical
        if non_num_cols and num_cols:
            cat_col = non_num_cols[0]
            val_col = num_cols[0]

            # If small category count (< 6 rows) and represents distribution
            if len(df) <= 5 and any(term in val_col.lower() for term in ["share", "percent", "count", "pct"]):
                return {
                    "chart_type": "pie",
                    "show_chart": True,
                    "names": cat_col,
                    "values": val_col,
                    "title": f"Distribution by {cat_col.replace('_', ' ').title()}"
                }

            # Standard bar chart
            return {
                "chart_type": "bar",
                "show_chart": True,
                "x": cat_col,
                "y": val_col,
                "title": f"{val_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}"
            }

        # Case 3: Two numerical columns
        if len(num_cols) >= 2:
            return {
                "chart_type": "scatter",
                "show_chart": True,
                "x": num_cols[0],
                "y": num_cols[1],
                "title": f"{num_cols[1].title()} vs {num_cols[0].title()}"
            }

        # Default fallback: table only
        return {"chart_type": "table_only", "show_chart": False, "reason": "Tabular format best"}

    BANNED_SUMMARY_PHRASES = (
        "we need",
        "let's craft",
        "must be under",
        "the user",
        "summariz",
    )
    NON_SUMMABLE_METRIC_KEYWORDS = (
        "avg",
        "average",
        "mean",
        "rate",
        "ratio",
        "pct",
        "percent",
        "score",
    )
    MONEY_COLUMN_KEYWORDS = (
        "revenue",
        "sales",
        "price",
        "amount",
        "cost",
        "tip",
        "spend",
        "payment",
        "total_value",
        "fee",
        "profit",
    )
    AGGREGATE_ALIAS_KEYWORDS = (
        "total",
        "sum",
        "count",
        "cnt",
        "avg",
        "average",
        "mean",
        "min",
        "max",
        "revenue",
        "sales",
        "spend",
    )
    DATE_COLUMN_KEYWORDS = (
        "date",
        "time",
        "sold_on",
        "created",
        "updated",
        "timestamp",
        "month",
        "year",
        "day",
    )

    @staticmethod
    def _is_id_or_rank_column(col_name: str) -> bool:
        """Returns True for ID, index, or rank columns that must never be described or totalled."""
        clower = str(col_name or "").strip().lower()
        return (
            clower == "id"
            or clower.endswith("_id")
            or clower.startswith("id_")
            or clower in ("rank", "row_num", "row_number", "rownum", "index", "idx")
            or clower.endswith("_rank")
            or clower.startswith("rank_")
            or clower.endswith("_index")
            or clower.startswith("index_")
        )

    @classmethod
    def _get_metric_numeric_columns(cls, df: pd.DataFrame) -> list:
        """Returns numeric columns excluding ID, index, and rank columns."""
        return [
            c for c in df.select_dtypes(include=[np.number]).columns.tolist()
            if not cls._is_id_or_rank_column(c)
        ]

    @classmethod
    def _is_money_column(cls, col_name: str) -> bool:
        """Returns True if the column/alias name indicates a monetary value."""
        clower = str(col_name or "").lower()
        return any(kw in clower for kw in cls.MONEY_COLUMN_KEYWORDS)

    @classmethod
    def _is_plain_row_listing(cls, df: pd.DataFrame, sql: str = "") -> bool:
        """
        Returns True when the result is a plain row listing (multiple rows, no SQL aggregate
        such as COUNT/SUM/AVG/MIN/MAX, no GROUP BY, and no aggregate-like column alias).
        """
        if df.empty or len(df) <= 1:
            return False

        sql_text = sql or ""
        if re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql_text, re.IGNORECASE):
            return False
        if re.search(r"\bGROUP\s+BY\b", sql_text, re.IGNORECASE):
            return False

        cols_lower = [str(c).lower() for c in df.columns]
        if any(any(kw in cl for kw in cls.AGGREGATE_ALIAS_KEYWORDS) for cl in cols_lower):
            return False

        has_id_col = any(cls._is_id_or_rank_column(c) for c in df.columns)
        return len(df) > 5 or has_id_col or len(df.columns) >= 4

    @classmethod
    def _build_row_listing_summary(cls, df: pd.DataFrame) -> str:
        """Builds a deterministic summary for plain row listings without leaders or totals."""
        n_rows = len(df)
        for col in df.columns:
            clower = str(col).lower()
            is_date_col = (
                pd.api.types.is_datetime64_any_dtype(df[col])
                or any(kw in clower for kw in cls.DATE_COLUMN_KEYWORDS)
                or clower.endswith("_on")
                or clower.endswith("_at")
            )
            if is_date_col:
                non_null = df[col].dropna()
                if not non_null.empty:
                    vals = non_null.astype(str)
                    min_val, max_val = vals.min(), vals.max()
                    if min_val != max_val:
                        return f"Showing {n_rows:,} rows from {min_val} to {max_val}."
                    return f"Showing {n_rows:,} rows for {min_val}."
        return f"Showing {n_rows:,} rows."

    @classmethod
    def _is_non_summable_metric(cls, col_name: str, sql: str = "") -> bool:
        """
        Returns True if the metric column represents an average, rate, ratio, percentage,
        or score (by column name or SQL AVG(...) alias) and therefore must never be summed.
        """
        col_lower = (col_name or "").lower()
        if any(kw in col_lower for kw in cls.NON_SUMMABLE_METRIC_KEYWORDS):
            return True
        if sql:
            escaped = re.escape(col_name)
            if re.search(rf'\bAVG\s*\([^)]*\)\s*(?:AS\s+)?["`\[]?{escaped}["`\]]?\b', sql, re.IGNORECASE):
                return True
            if re.search(r'\bAVG\s*\(', sql, re.IGNORECASE) and not re.search(r'\bSUM\s*\(', sql, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _format_number(value: Any) -> str:
        """Formats numeric values cleanly for spoken summaries."""
        num = float(value)
        if num.is_integer():
            return f"{int(round(num)):,}"
        return f"{num:,.2f}"

    @classmethod
    def _is_valid_summary(cls, text: str) -> bool:
        """Validates LLM-generated spoken summary text."""
        if not text or not text.strip():
            return False
        cleaned = text.strip()
        if len(cleaned.split()) > 40:
            return False
        lowered = cleaned.lower()
        if any(phrase in lowered for phrase in cls.BANNED_SUMMARY_PHRASES):
            return False
        if cleaned[-1] not in (".", "!", "?"):
            return False
        return True

    @classmethod
    def _all_metrics_zero_or_null(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Detects ranked/grouped item results where every metric value is zero or null.
        Returns the primary metric display name if so, otherwise None.
        """
        if df.empty:
            return None

        num_cols = cls._get_metric_numeric_columns(df)
        all_null_metric_cols = [
            c for c in df.columns[1:]
            if c not in num_cols and not cls._is_id_or_rank_column(c) and df[c].isna().all()
        ]
        metric_cols = num_cols + all_null_metric_cols
        if not metric_cols:
            return None

        # Only applies when ranking/listing items (multiple rows or label + metric columns)
        if len(df) <= 1 and len(df.columns) <= len(metric_cols):
            return None

        for col in metric_cols:
            non_null = df[col].dropna()
            if not non_null.empty and not (non_null == 0).all():
                return None

        return metric_cols[0].replace("_", " ").strip().lower()

    @classmethod
    def _build_template_summary(cls, df: pd.DataFrame, sql: str = "") -> str:
        """Builds a deterministic spoken summary strictly describing the returned rows."""
        if df.empty:
            return "No matching records were returned."

        if cls._is_plain_row_listing(df, sql):
            return cls._build_row_listing_summary(df)

        zero_metric = cls._all_metrics_zero_or_null(df)
        if zero_metric:
            return f"The query returned no {zero_metric} values, so the result may be incomplete."

        num_cols = cls._get_metric_numeric_columns(df)
        if num_cols:
            col = num_cols[0]
            numeric_series = df[col].dropna()
            if not numeric_series.empty:
                if len(df) > 1:
                    max_idx = numeric_series.idxmax()
                    max_val = numeric_series.loc[max_idx]
                    label_cols = [c for c in df.columns if c != col and not cls._is_id_or_rank_column(c)]
                    if not label_cols:
                        label_cols = [c for c in df.columns if c != col]
                    label_val = str(df.loc[max_idx, label_cols[0]]) if label_cols else "the top row"
                    formatted_max = cls._format_number(max_val)

                    if cls._is_non_summable_metric(col, sql):
                        min_idx = numeric_series.idxmin()
                        min_val = numeric_series.loc[min_idx]
                        low_label = str(df.loc[min_idx, label_cols[0]]) if label_cols else "the lowest row"
                        formatted_min = cls._format_number(min_val)
                        return (
                            f"Among the {len(df)} returned results, {label_val} is highest at {formatted_max}, "
                            f"while {low_label} is lowest at {formatted_min}."
                        )

                    total_val = numeric_series.sum()
                    formatted_total = cls._format_number(total_val)
                    if "limit" in (sql or "").lower() or len(df) in (10, 100):
                        return (
                            f"Among the top {len(df)} results, {label_val} leads with {formatted_max}. "
                            f"The rows shown total {formatted_total}."
                        )
                    return (
                        f"Among the {len(df)} returned results, {label_val} leads with {formatted_max}. "
                        f"The rows shown total {formatted_total}."
                    )
                else:
                    val = numeric_series.iloc[0]
                    formatted_val = cls._format_number(val)
                    col_title = col.replace("_", " ")
                    label_cols = [c for c in df.columns if c != col and not cls._is_id_or_rank_column(c)]
                    if label_cols:
                        label_val = str(df[label_cols[0]].iloc[0])
                        return f"The returned row shows {label_val} with {formatted_val} for {col_title}."
                    return f"The returned result shows {formatted_val} for {col_title}."

        row_word = "row" if len(df) == 1 else "rows"
        return f"The query returned {len(df)} {row_word}."

    def generate_spoken_insight(self, df: pd.DataFrame, question: str, sql: str) -> str:
        """
        Synthesizes the key statistical takeaway into 1-2 punchy spoken sentences.
        Emphasizes peak values, averages, minimums, and totals without reading the whole table.
        """
        if df.empty:
            return "No matching records were found for your query in the database."

        if self._is_plain_row_listing(df, sql):
            return self._build_row_listing_summary(df)

        zero_metric = self._all_metrics_zero_or_null(df)
        if zero_metric:
            return f"The query returned no {zero_metric} values, so the result may be incomplete."

        # Compute summary stats to provide rich context to LLM (excluding ID, index, and rank columns)
        num_cols = self._get_metric_numeric_columns(df)
        summary_facts = []
        is_non_summable = False
        is_money_metric = False
        
        if num_cols:
            primary_metric = num_cols[0]
            is_non_summable = self._is_non_summable_metric(primary_metric, sql)
            is_money_metric = self._is_money_column(primary_metric)
            try:
                max_val = df[primary_metric].max()
                min_val = df[primary_metric].min()
                
                # Check top and bottom rows
                top_row = df.loc[df[primary_metric].idxmax()]
                bottom_row = df.loc[df[primary_metric].idxmin()]
                label_cols = [c for c in df.columns if c != primary_metric and not self._is_id_or_rank_column(c)]
                if not label_cols:
                    label_cols = [c for c in df.columns if c != primary_metric]
                top_label = top_row[label_cols[0]] if label_cols else "Peak"
                bottom_label = bottom_row[label_cols[0]] if label_cols else "Lowest"
                
                if is_non_summable:
                    summary_facts.append(
                        f"Subset of {len(df)} rows (non-summable average/rate/score — NEVER sum or total): "
                        f"Highest '{top_label}' at {max_val:,.2f}, Lowest '{bottom_label}' at {min_val:,.2f}."
                    )
                else:
                    total_val = df[primary_metric].sum()
                    avg_val = df[primary_metric].mean()
                    summary_facts.append(
                        f"Subset of {len(df)} rows: Top '{top_label}' at {max_val:,.2f}, "
                        f"Average {avg_val:,.2f}, Sum of returned rows {total_val:,.2f}."
                    )
            except Exception:
                pass

        # Limit tabular preview to top 5 rows, excluding ID/rank columns so LLM never mistakes IDs for metrics
        preview_cols = [c for c in df.columns if not self._is_id_or_rank_column(c)] or list(df.columns)
        sample_data = df[preview_cols].head(5).to_dict(orient="records")

        highlight_rule = (
            "3. State the highest and lowest values. NEVER sum, add together, or report a total for this average/rate/score metric."
            if is_non_summable
            else "3. State the key highlight (explicitly mention the peak/top contributor or the total of these rows)."
        )
        currency_rule = (
            "4. NEVER attach a currency symbol ($, USD, dollars) to counts or quantities; only use currency for monetary metrics."
            if not is_money_metric
            else "4. Only use currency symbols for monetary values, never for counts or IDs."
        )

        prompt = f"""You are a voice executive business analyst. The user asked:
Question: "{question}"

EXECUTED SQL:
{sql}

RESULT SAMPLE:
{sample_data}

METRIC FACTS:
{summary_facts}

INSTRUCTIONS:
1. Explain the result in ONE punchy sentence strictly under 20 words for fast audio listening.
2. ACCURACY: You only have access to {len(df)} returned rows. If the query had a limit (e.g. top 10 or 100), phrase your summary strictly about the returned rows (e.g., 'Among the top {len(df)} records, X leads with...'). NEVER claim the returned sum represents all records across the whole database.
{highlight_rule}
{currency_rule}
5. NEVER read the raw table or recite column names.
6. Return ONLY the single spoken sentence.
"""

        try:
            create_kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 400,
            }
            if "gpt-oss" in (self.model or "").lower():
                create_kwargs["reasoning_effort"] = "low"
                create_kwargs["include_reasoning"] = False

            res = self.client.chat.completions.create(**create_kwargs)
            raw_text = (res.choices[0].message.content or "").strip().strip('"').strip("'").strip()
            if self._is_valid_summary(raw_text):
                if is_non_summable and re.search(
                    r"\b(total|totals|totaling|totalling|sum|combined)\b", raw_text, re.IGNORECASE
                ):
                    pass
                elif not is_money_metric and re.search(r"(\$|€|£|\bdollars?\b|\busd\b)", raw_text, re.IGNORECASE):
                    pass
                else:
                    return raw_text
        except Exception:
            pass

        # Robust deterministic analytical summary if LLM call fails or returns invalid/empty output
        return self._build_template_summary(df, sql)
