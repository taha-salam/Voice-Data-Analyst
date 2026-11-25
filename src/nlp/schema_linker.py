"""
Dynamic Schema Linker & Multi-Source Router:
1. MultiSourceRouter: Determines which connected database source (SQLite, PostgreSQL, CSV/DuckDB) answers the question.
2. SchemaLinker: Prunes large database schemas to select only the relevant tables, columns, and foreign-key bridges.
"""
import re
from typing import Dict, Any, List, Set, Tuple, Optional
from rapidfuzz import fuzz

class MultiSourceRouter:
    """Routes a business question to the most appropriate connected database source."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def route_query(self, query: str, profiles: Dict[str, Dict[str, Any]]) -> str:
        """
        Scores each database source against the user query.
        Returns the name of the winning database source.
        """
        query_lower = query.lower()
        source_scores: Dict[str, float] = {}
        
        for src_name, profile in profiles.items():
            score = 0.0
            tables = profile.get("tables", {})
            
            # Check table names
            for tname, meta in tables.items():
                t_clean = tname.lower().replace("_", " ")
                if t_clean in query_lower or tname.lower() in query_lower:
                    score += 5.0
                elif fuzz.partial_ratio(t_clean, query_lower) > 75:
                    score += 2.0
                    
                # Check column names
                for col in meta.get("columns", []):
                    cname = col["name"].lower().replace("_", " ")
                    if len(cname) > 3 and cname in query_lower:
                        score += 3.0
                        
                # Check sample values
                for col_name, samples in meta.get("sample_values", {}).items():
                    for s in samples:
                        s_str = str(s).lower()
                        if len(s_str) > 2 and s_str in query_lower:
                            score += 4.0
                            
            source_scores[src_name] = score

        # If highest score > 0, return that source; otherwise default to primary source ('olist' or first)
        best_source = max(source_scores.items(), key=lambda x: x[1], default=("olist", 0.0))
        if best_source[1] > 0:
            return best_source[0]
            
        # Default fallback
        if "olist" in profiles:
            return "olist"
        return next(iter(profiles.keys())) if profiles else "olist"


class SchemaLinker:
    """Prunes a large database schema into a compact prompt containing only relevant tables and relationships."""
    
    # Semantic keyword mappings for business queries
    CONCEPT_KEYWORDS = {
        "revenue": ["price", "freight_value", "payment_value", "actual_sales"],
        "sales": ["price", "order_items", "actual_sales", "orders"],
        "price": ["price", "unit_cost"],
        "cost": ["price", "unit_cost", "freight_value"],
        "freight": ["freight_value", "shipping_limit_date"],
        "rating": ["review_score", "order_reviews"],
        "review": ["review_score", "order_reviews", "review_comment_message"],
        "delivery": ["order_delivered_customer_date", "order_estimated_delivery_date"],
        "time": ["order_purchase_timestamp", "last_restocked"],
        "month": ["order_purchase_timestamp", "shipping_limit_date"],
        "quarter": ["order_purchase_timestamp"],
        "year": ["order_purchase_timestamp"],
        "stock": ["quantity_on_hand", "inventory_stock", "reorder_level"],
        "warehouse": ["warehouses", "capacity_units"],
        "supplier": ["suppliers", "rating", "lead_time_days"],
        "commission": ["commission_rate", "sales_reps"],
        "city": ["customer_city", "seller_city", "city"],
        "customer": ["customers", "customer_id", "customer_unique_id"],
        "product": ["products", "product_id", "product_category_name", "product_name"],
        "seller": ["sellers", "seller_id"]
    }

    def __init__(self, profile: Dict[str, Any]):
        self.profile = profile
        self.tables = profile.get("tables", {})
        self.fk_graph = self._build_fk_graph()

    def _build_fk_graph(self) -> Dict[str, Set[str]]:
        """Builds an undirected adjacency graph of tables connected by foreign keys or common ID columns."""
        graph = {t: set() for t in self.tables}
        
        # 1. Direct declared foreign keys
        for table, meta in self.tables.items():
            for fk in meta.get("foreign_keys", []):
                to_tbl = fk.get("to_table")
                if to_tbl in graph:
                    graph[table].add(to_tbl)
                    graph[to_tbl].add(table)
                    
        # 2. Heuristic ID-based column name matching (e.g. customer_id across orders and customers)
        col_to_tables = {}
        for table, meta in self.tables.items():
            for col in meta.get("columns", []):
                cname = col["name"].lower()
                if cname.endswith("_id") or cname == "id":
                    col_to_tables.setdefault(cname, set()).add(table)
                    
        for cname, tbls in col_to_tables.items():
            for t1 in tbls:
                for t2 in tbls:
                    if t1 != t2:
                        graph[t1].add(t2)
                        graph[t2].add(t1)
                        
        return graph

    def link_schema(self, query: str, max_tables: int = 4) -> Dict[str, Any]:
        """Scores each table based on query term overlap, semantic concepts, and selects the minimal connected subgraph."""
        query_lower = query.lower()
        query_words = set(re.findall(r'\b[a-z0-9_]+\b', query_lower))
        
        table_scores: Dict[str, float] = {}
        
        for tname, meta in self.tables.items():
            score = 0.0
            t_clean = tname.lower().replace("_", " ")
            
            # Match table name directly
            if tname.lower() in query_words or any(w in t_clean for w in query_words if len(w) > 3):
                score += 5.0
            table_ratio = fuzz.partial_ratio(t_clean, query_lower)
            if table_ratio > 70:
                score += (table_ratio / 20.0)
                
            # Match column names
            for col in meta.get("columns", []):
                cname = col["name"].lower()
                c_clean = cname.replace("_", " ")
                if cname in query_words or any(w in c_clean for w in query_words if len(w) > 3):
                    score += 3.0
                elif fuzz.partial_ratio(c_clean, query_lower) > 80:
                    score += 1.5
                    
            # Match business concept keywords
            for concept, mapped_cols in self.CONCEPT_KEYWORDS.items():
                if concept in query_lower:
                    for col in meta.get("columns", []):
                        if any(col["name"].lower() == mc.lower() or tname.lower() == mc.lower() for mc in mapped_cols):
                            score += 4.0
                            break
                            
            # Match sample values
            for col_name, samples in meta.get("sample_values", {}).items():
                for s in samples:
                    s_lower = str(s).lower()
                    if len(s_str := s_lower.replace("_", " ")) > 2 and (s_lower in query_lower or s_str in query_lower):
                        score += 5.0
                        break
                        
            table_scores[tname] = score

        # Sort tables by score descending
        sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top tables with non-zero scores (or at least top 1)
        selected: Set[str] = set()
        for tname, score in sorted_tables:
            if score > 0 and len(selected) < max_tables:
                selected.add(tname)
                
        if not selected and self.tables:
            selected = set(list(self.tables.keys())[:2])

        # Connect isolated selected tables via bridge tables if available
        connected_selected = set(selected)
        sel_list = list(selected)
        for i in range(len(sel_list)):
            for j in range(i + 1, len(sel_list)):
                t1, t2 = sel_list[i], sel_list[j]
                if t2 not in self.fk_graph.get(t1, set()):
                    common_bridges = self.fk_graph.get(t1, set()).intersection(self.fk_graph.get(t2, set()))
                    if common_bridges:
                        connected_selected.add(next(iter(common_bridges)))

        # Format compact schema definition
        compact_schema = []
        for tname in connected_selected:
            meta = self.tables[tname]
            cols = [f"{c['name']} ({c['type']})" for c in meta.get("columns", [])]
            pks = meta.get("primary_keys", [])
            fks = [
                f"{fk['from_column']} -> {fk['to_table']}({fk['to_column']})"
                for fk in meta.get("foreign_keys", [])
                if fk['to_table'] in connected_selected
            ]
            
            # Format samples
            sample_str_list = []
            for col, samples in meta.get("sample_values", {}).items():
                if samples:
                    sample_str_list.append(f"{col}: [{', '.join(samples[:3])}]")
            
            compact_schema.append(
                f"TABLE: {tname}\n"
                f"  Columns: {', '.join(cols)}\n"
                f"  Primary Keys: {', '.join(pks) if pks else 'None'}\n"
                f"  Relationships: {'; '.join(fks) if fks else 'None'}\n"
                f"  Sample Values: {'; '.join(sample_str_list[:4]) if sample_str_list else 'None'}"
            )
            
        return {
            "selected_tables": list(connected_selected),
            "schema_prompt": "\n\n".join(compact_schema)
        }
