"""
Safety Guardrails and Attack Refusal Engine:
Enforces strict read-only query execution and prevents destructive operations and SQL injection.
Uses AST validation via sqlglot and prompt injection detection.
"""
import re
from typing import Tuple, List, Optional
import sqlglot
from sqlglot import exp

class SafetyGuardrail:
    """Validates SQL queries and refuses dangerous, destructive, or unauthorized requests."""

    # Disallowed SQL statement types in AST
    FORBIDDEN_AST_NODES = (
        exp.Drop,
        exp.Delete,
        exp.Update,
        exp.Insert,
        exp.Create,
        exp.Alter,
        exp.TruncateTable,
        exp.Command,
        exp.Pragma,
        exp.Kill
    )

    # Disallowed regex patterns
    FORBIDDEN_KEYWORDS_REGEX = re.compile(
        r'\b(DROP\s+TABLE|DROP\s+VIEW|DROP\s+DATABASE|DELETE\s+FROM|TRUNCATE\s+TABLE|'
        r'UPDATE\s+\w+\s+SET|INSERT\s+INTO|ALTER\s+TABLE|CREATE\s+TABLE|CREATE\s+VIEW|'
        r'ATTACH\s+DATABASE|DETACH\s+DATABASE|GRANT\s+|REVOKE\s+|PRAGMA\s+writable_schema)\b',
        re.IGNORECASE
    )

    # Adversarial prompt injection keywords
    ADVERSARIAL_PROMPT_PATTERNS = [
        re.compile(r'ignore\s+(all\s+)?(previous|prior)\s+instructions', re.IGNORECASE),
        re.compile(r'system\s+prompt', re.IGNORECASE),
        re.compile(r'you\s+are\s+now\s+in\s+developer\s+mode', re.IGNORECASE),
        re.compile(r'bypass\s+(safety|guardrails)', re.IGNORECASE),
        re.compile(r'drop\s+all\s+tables', re.IGNORECASE),
        re.compile(r'delete\s+all\s+records', re.IGNORECASE)
    ]

    @classmethod
    def check_user_intent_safety(cls, user_question: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects natural language prompt for malicious intent before generating SQL.
        Returns (is_safe, refusal_reason).
        """
        q_lower = user_question.lower()
        
        # Check malicious patterns
        for pattern in cls.ADVERSARIAL_PROMPT_PATTERNS:
            if pattern.search(user_question):
                return False, "Dangerous request refused: The question attempts to modify database state or bypass safety instructions."

        # Check explicit destructive words
        destructive_actions = ["drop table", "delete table", "delete all", "truncate table", "wipe database", "remove all data"]
        if any(action in q_lower for action in destructive_actions):
            return False, "Dangerous request refused: Destructive actions (DROP, DELETE, TRUNCATE) are strictly prohibited."

        return True, None

    @classmethod
    def validate_sql(cls, sql_query: str, dialect: str = "sqlite") -> Tuple[bool, Optional[str]]:
        """
        Performs deep AST inspection on the SQL query.
        Guarantees that ONLY read-only SELECT queries are executed.
        Refuses multi-query piggybacking and destructive statements.
        """
        if not sql_query or not sql_query.strip():
            return False, "Query is empty."

        # Strip any markdown code fences if present
        clean_sql = re.sub(r'^```(?:sql)?\s*', '', sql_query.strip(), flags=re.IGNORECASE)
        clean_sql = re.sub(r'\s*```$', '', clean_sql.strip()).strip().rstrip(';')

        # 1. Regex check for hard-coded forbidden keywords
        if cls.FORBIDDEN_KEYWORDS_REGEX.search(clean_sql):
            return False, "Dangerous query refused: Destructive SQL keyword detected."

        # 2. Parse SQL AST using sqlglot
        try:
            glot_dialect = "sqlite" if dialect in ("sqlite", "duckdb") else "postgres"
            statements = sqlglot.parse(clean_sql, read=glot_dialect)
        except Exception as e:
            # If it cannot be parsed, reject for safety
            return False, f"SQL syntax could not be parsed safely: {e}"

        # Refuse multiple statements (piggybacking attacks)
        if len(statements) > 1:
            return False, "Dangerous query refused: Multiple stacked queries (piggybacking) are not allowed."

        if not statements or statements[0] is None:
            return False, "Empty query statement."

        stmt = statements[0]

        # 3. Check for any forbidden nodes in AST tree
        for node in stmt.walk():
            if isinstance(node, cls.FORBIDDEN_AST_NODES):
                return False, f"Dangerous query refused: Found disallowed statement node '{node.__class__.__name__}'."

        # 4. Ensure top-level root is a SELECT expression
        if not isinstance(stmt, (exp.Select, exp.Union)):
            return False, f"Dangerous query refused: Root statement must be a SELECT, found '{stmt.__class__.__name__}'."

        return True, None
