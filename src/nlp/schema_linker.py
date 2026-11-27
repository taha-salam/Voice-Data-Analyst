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

    # Semantic intent boosts mapping query concepts to database signature columns and tables
    DOMAIN_INTENT_BOOSTS = {
        # E-Commerce, orders, revenue, customers -> Olist
        "revenue": ["payment_value", "price", "order_payments", "orders", "order_items", "actual_sales"],
        "sales": ["order_items", "orders", "price", "actual_sales"],
        "order": ["orders", "order_items", "order_status"],
        "orders": ["orders", "order_items", "order_status"],
        "customer": ["customers", "customer_id", "customer_city", "customer_state"],
        "customers": ["customers", "customer_id", "customer_city", "customer_state"],
        "buyer": ["customers"],
        "buyers": ["customers"],
        "delivery": ["order_delivered_customer_date", "order_estimated_delivery_date"],
        "delivered": ["order_delivered_customer_date", "order_status"],
        "shipping": ["freight_value", "shipping_limit_date"],
        "freight": ["freight_value"],
        "review": ["order_reviews", "review_score"],
        "reviews": ["order_reviews", "review_score"],
        "payment": ["order_payments", "payment_type", "payment_value"],
        "payments": ["order_payments", "payment_type", "payment_value"],
        "category": ["product_category_name", "product_category_name_translation", "category"],
        "categories": ["product_category_name", "product_category_name_translation", "category"],
        
        # Supply chain, warehousing, physical stock -> Inventory
        "stock": ["inventory_stock", "quantity", "quantity_on_hand", "stock_quantity", "reorder_level"],
        "inventory": ["inventory_stock", "inventory_id", "warehouses"],
        "warehouse": ["warehouses", "warehouse_name", "warehouse_id", "location_city"],
        "warehouses": ["warehouses", "warehouse_name", "warehouse_id", "location_city"],
        "supplier": ["suppliers", "supplier_name", "lead_time_days"],
        "suppliers": ["suppliers", "supplier_name", "lead_time_days"],
        "restock": ["reorder_level", "quantity"],
        "lead time": ["lead_time_days"],

        # Sales Representatives & Quotas -> CSV / DuckDB
        "rep": ["sales_reps", "rep_name", "rep_id"],
        "reps": ["sales_reps", "rep_name", "rep_id"],
        "representative": ["sales_reps", "rep_name"],
        "representatives": ["sales_reps", "rep_name"],
        "quota": ["target_sales", "target_quota"],
        "quotas": ["target_sales", "target_quota"],
        "commission": ["commission_rate"],
        "commissions": ["commission_rate"],
        "target": ["target_sales", "target_quota"]
    }
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def route_query_detailed(self, query: str, profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scores each database source against the user query using table names, column semantics,
        sample values, and domain concept boosts.
        Returns a detailed dictionary with the chosen source, per-source scores, matched terms, and confidence.
        """
        query_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', query_lower))
        source_scores: Dict[str, float] = {}
        matched_terms: Dict[str, List[str]] = {}
        
        for src_name, profile in profiles.items():
            score = 0.0
            reasons = []
            tables = profile.get("tables", {})

            all_col_names = []
            all_table_names = list(tables.keys())
            for tname, meta in tables.items():
                all_col_names.extend([c["name"].lower() for c in meta.get("columns", [])])

            # 1. Domain Intent Boosts (Semantic concept matching)
            for concept, target_signatures in self.DOMAIN_INTENT_BOOSTS.items():
                if concept in words or concept in query_lower:
                    matched_in_src = False
                    for sig in target_signatures:
                        if sig in all_table_names:
                            score += 8.0
                            reasons.append(f"concept '{concept}' matched table '{sig}'")
                            matched_in_src = True
                            break
                        elif any(sig in cname for cname in all_col_names):
                            score += 6.0
                            reasons.append(f"concept '{concept}' matched column '{sig}'")
                            matched_in_src = True
                            break
            
            # 2. Direct table name matching
            for tname, meta in tables.items():
                t_clean = tname.lower().replace("_", " ")
                if t_clean in query_lower or tname.lower() in query_lower:
                    score += 5.0
                    reasons.append(f"table '{tname}'")
                elif fuzz.partial_ratio(t_clean, query_lower) > 75:
                    score += 2.0
                    
                # 3. Direct column name matching
                for col in meta.get("columns", []):
                    cname = col["name"].lower().replace("_", " ")
                    if len(cname) > 3 and cname in query_lower:
                        score += 3.0
                        reasons.append(f"column '{col['name']}' in '{tname}'")
                    elif any(w in cname for w in words if len(w) > 4):
                        score += 1.5
                        
                # 4. Sample value matching
                for col_name, samples in meta.get("sample_values", {}).items():
                    for s in samples:
                        s_str = str(s).lower()
                        if len(s_str) > 2 and s_str in query_lower:
                            score += 4.0
                            reasons.append(f"sample '{s_str}' in '{col_name}'")
                            
            source_scores[src_name] = round(score, 2)
            matched_terms[src_name] = reasons

        # Pick highest scoring source
        sorted_sources = sorted(source_scores.items(), key=lambda x: x[1], reverse=True)
        best_source, best_score = sorted_sources[0] if sorted_sources else ("olist", 0.0)
        
        # Check if top two are tied or very close (ambiguity detection)
        is_ambiguous = False
        confidence = 1.0
        if len(sorted_sources) > 1 and best_score > 0:
            second_source, second_score = sorted_sources[1]
            if second_score > 0:
                confidence = round((best_score - second_score) / best_score, 2)
                if confidence < 0.15:
                    is_ambiguous = True

        if best_score <= 0.0:
            # Fallback to olist or first available source
            best_source = "olist" if "olist" in profiles else (next(iter(profiles.keys())) if profiles else "olist")
            confidence = 0.5

        return {
            "source": best_source,
            "scores": source_scores,
            "matched_terms": matched_terms.get(best_source, []),
            "all_matches": matched_terms,
            "confidence": confidence,
            "is_ambiguous": is_ambiguous
        }

    def route_query(self, query: str, profiles: Dict[str, Dict[str, Any]]) -> str:
        """
        Scores each database source against the user query.
        Returns the name of the winning database source.
        """
        return self.route_query_detailed(query, profiles)["source"]


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
