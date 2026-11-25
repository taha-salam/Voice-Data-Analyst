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

    def generate_spoken_insight(self, df: pd.DataFrame, question: str, sql: str) -> str:
        """
        Synthesizes the key statistical takeaway into 1-2 punchy spoken sentences.
        Emphasizes peak values, averages, minimums, and totals without reading the whole table.
        """
        if df.empty:
            return "No matching records were found for your query in the database."

        # Compute summary stats to provide rich context to LLM
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        summary_facts = []
        
        if num_cols:
            primary_metric = num_cols[0]
            try:
                total_val = df[primary_metric].sum()
                avg_val = df[primary_metric].mean()
                max_val = df[primary_metric].max()
                min_val = df[primary_metric].min()
                
                # Check top row
                top_row = df.loc[df[primary_metric].idxmax()]
                label_cols = [c for c in df.columns if c != primary_metric]
                top_label = top_row[label_cols[0]] if label_cols else "Peak"
                
                summary_facts.append(f"Primary Metric '{primary_metric}': Top '{top_label}' at {max_val:,.2f}, Average {avg_val:,.2f}, Total {total_val:,.2f}.")
            except Exception:
                pass

        # Limit tabular preview to top 5 rows
        sample_data = df.head(5).to_dict(orient="records")

        prompt = f"""You are a voice executive business analyst. The user asked:
Question: "{question}"

EXECUTED SQL:
{sql}

RESULT SAMPLE:
{sample_data}

METRIC FACTS:
{summary_facts}

INSTRUCTIONS:
1. Explain the result in 1 to 2 short sentences designed for audio listening.
2. State the key highlight (explicitly mention the peak/top contributor or the total).
3. NEVER read the raw table or recite column names.
4. Keep the voice confident, natural, and conversational.
5. Return ONLY the spoken sentences.
"""

        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=250
            )
            raw_text = res.choices[0].message.content or ""
            if not raw_text.strip() and hasattr(res.choices[0].message, "reasoning"):
                raw_text = getattr(res.choices[0].message, "reasoning", "")
            raw_text = raw_text.strip().strip('"').strip("'")
            if raw_text:
                return raw_text
        except Exception:
            pass

        # Robust deterministic analytical summary if LLM call fails or returns empty
        if not df.empty:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols and len(df) > 1:
                col = num_cols[0]
                max_idx = df[col].idxmax()
                label_cols = [c for c in df.columns if c != col]
                label_val = df.loc[max_idx, label_cols[0]] if label_cols else "peak"
                return f"Across {len(df)} records, {label_val} had the highest {col.replace('_', ' ')} at {df[col].max():,.2f}, with a total of {df[col].sum():,.2f}."
            elif num_cols and len(df) == 1:
                col = num_cols[0]
                return f"The total {col.replace('_', ' ')} is {df[col].iloc[0]:,.2f} across the selected records."
        return f"The query returned {len(df)} matching records successfully."
