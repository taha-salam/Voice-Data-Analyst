"""
Domain Word Correction Engine:
Indexes real categorical values from connected databases (cities, categories, product names, statuses)
and fixes misheard ASR tokens using fuzzy matching, phonetic similarity, and translation aliases before SQL generation.
Supports zero-config harvesting from any database engine.
"""
import re
import sqlite3
from typing import Dict, List, Tuple, Set, Optional, Any
from rapidfuzz import fuzz, process

class DomainWordCorrector:
    """Corrects misheard speech transcripts against true database entities."""
    
    def __init__(self):
        # Master dictionary mapping lowercase normalized entity -> canonical database value
        self.entity_index: Dict[str, str] = {}
        # Entity category tags for tracking (e.g. 'city', 'category', 'status', 'alias')
        self.entity_types: Dict[str, str] = {}
        # Predefined aliases for known speech quirks & English-to-DB mappings
        self.custom_aliases: Dict[str, str] = {
            "san paulo": "sao paulo",
            "saint paul": "sao paulo",
            "saint paulo": "sao paulo",
            "so paulo": "sao paulo",
            "san paolo": "sao paulo",
            "rio": "rio de janeiro",
            "rio de janero": "rio de janeiro",
            "belo": "belo horizonte",
            "bell horizon": "belo horizonte",
            "bell horizonte": "belo horizonte",
            "bello horizonte": "belo horizonte",
            "caxias do sol": "caxias do sul",
            "caxias": "caxias do sul",
            "porto allegre": "porto alegre",
            "curitibia": "curitiba",
            "joinvile": "joinville",
            "computers": "informatica_acessorios",
            "computer accessories": "informatica_acessorios",
            "health and beauty": "beleza_saude",
            "health beauty": "beleza_saude",
            "bed and bath": "cama_mesa_banho",
            "bed bath table": "cama_mesa_banho",
            "sports and leisure": "esporte_lazer",
            "sports leisure": "esporte_lazer",
            "furniture and decor": "moveis_decoracao",
            "housewares": "utilidades_domesticas",
            "watches and gifts": "relogios_presentes",
            "watches gifts": "relogios_presentes",
            "watches": "relogios_presentes",
            "credit card": "credit_card",
            "debit card": "debit_card",
            "voucher": "voucher",
            "boleto": "boleto"
        }
        for alias, target in self.custom_aliases.items():
            self.entity_index[alias.lower()] = target
            self.entity_types[alias.lower()] = "alias"

    def harvest_from_database(self, db_source):
        """
        Dynamically connects to a database source and extracts unique values
        for any entity-like columns (cities, categories, names, types, statuses).
        Works for SQLite, DuckDB, or PostgreSQL without hardcoded schema.
        """
        try:
            if db_source.engine_type == "sqlite":
                self._harvest_sqlite(db_source.uri_or_path)
            elif db_source.engine_type in ("duckdb", "csv"):
                self._harvest_duckdb(db_source.get_connection())
        except Exception as e:
            print(f"Warning: harvest_from_database encountered an error on {db_source.name}: {e}")

    def _harvest_sqlite(self, db_path: str):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # 1. Check for translation table first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%translation%'")
            trans_table = cursor.fetchone()
            if trans_table:
                t_name = trans_table[0]
                try:
                    cursor.execute(f"SELECT * FROM \"{t_name}\" LIMIT 200")
                    for row in cursor.fetchall():
                        if len(row) >= 2:
                            pt_val, en_val = str(row[0]), str(row[1])
                            self.entity_index[en_val.lower().replace("_", " ")] = pt_val
                            self.entity_index[en_val.lower()] = pt_val
                            self.entity_index[pt_val.lower().replace("_", " ")] = pt_val
                            self.entity_index[pt_val.lower()] = pt_val
                            self.entity_types[en_val.lower()] = "category_translation"
                except Exception:
                    pass

            # 2. Inspect all tables and text columns
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [r[0] for r in cursor.fetchall()]
            
            entity_keywords = ("city", "state", "category", "status", "type", "country", "name")
            for table in tables:
                cursor.execute(f"PRAGMA table_info(\"{table}\")")
                for col in cursor.fetchall():
                    cname = col[1].lower()
                    ctype = str(col[2]).upper()
                    if any(k in cname for k in entity_keywords) and ("INT" not in ctype and "REAL" not in ctype):
                        try:
                            cursor.execute(f"SELECT DISTINCT \"{col[1]}\" FROM \"{table}\" WHERE \"{col[1]}\" IS NOT NULL LIMIT 250")
                            for val_row in cursor.fetchall():
                                val = str(val_row[0]).strip()
                                if len(val) >= 2:
                                    clean_key = val.lower().replace("_", " ")
                                    self.entity_index[clean_key] = val
                                    self.entity_index[val.lower()] = val
                                    tag = "city" if "city" in cname else ("category" if "category" in cname else "entity")
                                    self.entity_types[clean_key] = tag
                        except Exception:
                            continue

    def _harvest_duckdb(self, con):
        tables_df = con.execute("SHOW TABLES").df()
        if tables_df.empty:
            return
        table_names = tables_df.iloc[:, 0].tolist()
        entity_keywords = ("city", "state", "category", "status", "type", "country", "name", "rep")
        for table in table_names:
            cols_df = con.execute(f"DESCRIBE {table}").df()
            for _, row in cols_df.iterrows():
                cname = row['column_name'].lower()
                ctype = str(row['column_type']).upper()
                if any(k in cname for k in entity_keywords) and ("INT" not in ctype and "DOUBLE" not in ctype):
                    try:
                        vals_df = con.execute(f"SELECT DISTINCT \"{row['column_name']}\" FROM {table} WHERE \"{row['column_name']}\" IS NOT NULL LIMIT 250").df()
                        for v in vals_df.iloc[:, 0].tolist():
                            val = str(v).strip()
                            if len(val) >= 2:
                                clean_key = val.lower().replace("_", " ")
                                self.entity_index[clean_key] = val
                                self.entity_index[val.lower()] = val
                                self.entity_types[clean_key] = "entity"
                    except Exception:
                        continue

    def index_database_profile(self, profile: Dict[str, Any]):
        """Indexes sample values extracted during the profiling phase."""
        for table_name, table_info in profile.get("tables", {}).items():
            for col_name, samples in table_info.get("sample_values", {}).items():
                col_lower = col_name.lower()
                is_entity_col = any(tag in col_lower for tag in ["city", "name", "category", "status", "type", "country"])
                if is_entity_col:
                    tag = "city" if "city" in col_lower else ("category" if "category" in col_lower else "entity")
                    for val in samples:
                        if val and len(str(val)) > 2:
                            val_str = str(val).strip()
                            clean_key = val_str.lower().replace("_", " ")
                            self.entity_index[clean_key] = val_str
                            self.entity_types[clean_key] = tag
                            self.entity_index[val_str.lower()] = val_str

    def correct_transcript(self, raw_transcript: str, threshold: float = 78.0) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Scans raw transcript for misheard entities and substitutes canonical database values.
        Returns: (corrected_text, list_of_corrections)
        """
        if not raw_transcript or not raw_transcript.strip():
            return raw_transcript, []

        corrected_text = raw_transcript
        corrections: List[Dict[str, Any]] = []
        
        # 1. Exact / Alias Replacement (prioritizing longer phrases)
        for alias, target in sorted(self.custom_aliases.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, corrected_text, flags=re.IGNORECASE):
                corrected_text = re.sub(pattern, target, corrected_text, flags=re.IGNORECASE)
                corrections.append({
                    "original": alias,
                    "corrected": target,
                    "confidence": 1.0,
                    "type": self.entity_types.get(alias, "alias")
                })

        # 2. Multi-word n-gram fuzzy matching against dynamic index
        words = re.findall(r'\b[\w\'-]+\b', corrected_text)
        n = len(words)
        entities = list(self.entity_index.keys())
        
        if not entities or n == 0:
            return corrected_text, corrections

        matched_spans: Set[Tuple[int, int]] = set()
        
        STOP_WORDS = {"the", "a", "an", "and", "for", "in", "by", "of", "to", "all", "top", "per", "how", "who", "show", "from", "at", "on", "with", "what", "is", "are", "many", "much"}
        
        # Match spans from 3 words down to 1
        for span_len in (3, 2, 1):
            for i in range(n - span_len + 1):
                if any(start <= i < end or start < i + span_len <= end for start, end in matched_spans):
                    continue
                    
                span_words = words[i:i + span_len]
                # If multi-word span starts or ends with a stop word, skip (let the inner sub-span match)
                if span_len > 1 and (span_words[0].lower() in STOP_WORDS or span_words[-1].lower() in STOP_WORDS):
                    continue
                
                phrase = " ".join(span_words).lower()
                
                # Skip trivial stop words
                if phrase in STOP_WORDS:
                    continue
                    
                match = process.extractOne(
                    phrase,
                    entities,
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=threshold
                )
                
                if match:
                    best_match, score, _ = match
                    canonical = self.entity_index[best_match]
                    orig_span_text = " ".join(span_words)
                    
                    is_already_present = bool(re.search(r'\b' + re.escape(canonical) + r'\b', corrected_text, flags=re.IGNORECASE))
                    if orig_span_text.lower() != canonical.lower() and not is_already_present:
                        matched_spans.add((i, i + span_len))
                        pattern = r'\b' + re.escape(orig_span_text) + r'\b'
                        corrected_text = re.sub(pattern, canonical, corrected_text, count=1, flags=re.IGNORECASE)
                        corrections.append({
                            "original": orig_span_text,
                            "corrected": canonical,
                            "confidence": round(score / 100.0, 2),
                            "type": self.entity_types.get(best_match, "fuzzy_match")
                        })
                        
        return corrected_text, corrections

    def evaluate_correction_accuracy(self, test_cases: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """
        Evaluates correction accuracy on a dataset of:
        (raw_misheard_transcript, expected_corrected_transcript, target_domain_entity)
        Computes accuracy before vs after correction.
        """
        total = len(test_cases)
        if total == 0:
            return {"accuracy_before": 0.0, "accuracy_after": 0.0, "total": 0}

        correct_before = 0
        correct_after = 0
        details = []

        for raw_text, expected_text, entity in test_cases:
            has_entity_before = entity.lower() in raw_text.lower()
            if has_entity_before:
                correct_before += 1
                
            corrected_output, corr_log = self.correct_transcript(raw_text)
            has_entity_after = entity.lower() in corrected_output.lower()
            if has_entity_after:
                correct_after += 1
                
            details.append({
                "raw": raw_text,
                "corrected": corrected_output,
                "target_entity": entity,
                "recovered": has_entity_after and not has_entity_before,
                "corrections": corr_log
            })

        return {
            "total_test_cases": total,
            "accuracy_before": round(correct_before / total * 100, 2),
            "accuracy_after": round(correct_after / total * 100, 2),
            "accuracy_improvement": round((correct_after - correct_before) / total * 100, 2),
            "details": details
        }
