"""
Comprehensive test suite for Phase 3: Domain Word Correction and Dynamic Schema Linker.
Performs heavy testing across various entity types, speech misrecognitions, and schema routing.
"""
import pytest
from src.config import Config
from src.db.connector import DatabaseManager
from src.db.profiler import DatabaseProfiler
from src.nlp.domain_corrector import DomainWordCorrector
from src.nlp.schema_linker import SchemaLinker, MultiSourceRouter

@pytest.fixture(scope="module")
def setup_phase3():
    """Sets up databases, profiles, and harvests domain entities."""
    Config.ensure_directories()
    db_mgr = DatabaseManager()
    
    olist_src = db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH), "Olist Brazilian E-Commerce")
    sec_src = db_mgr.register_sqlite("inventory", str(Config.SECONDARY_DB_PATH), "Inventory & Warehouses")
    csv_path = Config.DATA_DIR / "sample_csvs" / "sales_representatives.csv"
    csv_src = db_mgr.register_csv("sales_csv", str(csv_path), "sales_reps", "Sales Representatives")
    
    # Profiles
    profiles = {
        "olist": DatabaseProfiler(olist_src).profile(sample_limit=8),
        "inventory": DatabaseProfiler(sec_src).profile(sample_limit=8),
        "sales_csv": DatabaseProfiler(csv_src).profile(sample_limit=8)
    }
    
    # Initialize Corrector and harvest
    corrector = DomainWordCorrector()
    corrector.harvest_from_database(olist_src)
    corrector.harvest_from_database(sec_src)
    corrector.harvest_from_database(csv_src)
    
    return {
        "db_mgr": db_mgr,
        "profiles": profiles,
        "corrector": corrector
    }

def test_domain_corrector_harvesting(setup_phase3):
    """Verify that entity indexing harvested real database values dynamically."""
    corrector = setup_phase3["corrector"]
    index = corrector.entity_index
    
    # Check Brazilian cities
    assert "sao paulo" in index
    assert "rio de janeiro" in index
    assert "belo horizonte" in index
    assert "curitiba" in index
    
    # Check categories & translations
    assert "beleza_saude" in index.values() or "beleza_saude" in index
    assert "informatica_acessorios" in index.values() or "informatica_acessorios" in index
    assert "cama_mesa_banho" in index.values() or "cama_mesa_banho" in index
    
    # Check secondary DB entities
    assert "boston" in index
    assert "chicago" in index

    # Test removing entities from a specific source
    corrector.remove_from_source("inventory")
    # Custom aliases like sao paulo should remain, but inventory entities harvested are removed
    assert "sao paulo" in corrector.entity_index

def test_domain_word_correction_cities(setup_phase3):
    """Test correction of commonly misheard city names."""
    corrector = setup_phase3["corrector"]
    
    test_cases = [
        ("show me total orders in san paulo", "sao paulo"),
        ("which customers are located in rio", "rio de janeiro"),
        ("total sales in bell horizon", "belo horizonte"),
        ("sellers located in salvadorr", "salvador"),
        ("order volume in so paulo", "sao paulo")
    ]
    
    for raw_query, expected_entity in test_cases:
        corrected, log = corrector.correct_transcript(raw_query)
        assert expected_entity in corrected.lower(), f"Failed to correct '{raw_query}', got '{corrected}'"
        assert len(log) > 0, f"Expected correction log for '{raw_query}'"

def test_domain_word_correction_categories(setup_phase3):
    """Test translation and phonetic alignment of product categories."""
    corrector = setup_phase3["corrector"]
    
    test_cases = [
        ("what are top products in computer accessories", "informatica_acessorios"),
        ("how much revenue from health and beauty", "beleza_saude"),
        ("find orders for bed and bath", "cama_mesa_banho"),
        ("total purchases in sports and leisure", "esporte_lazer")
    ]
    
    for raw_query, expected_category in test_cases:
        corrected, log = corrector.correct_transcript(raw_query)
        assert expected_category in corrected.lower(), f"Failed for '{raw_query}': got '{corrected}'"

def test_domain_correction_accuracy_benchmark(setup_phase3):
    """Verify evaluation metric computation (accuracy before vs after correction) for Module 10."""
    corrector = setup_phase3["corrector"]
    
    benchmark_dataset = [
        ("orders in san paulo", "orders in sao paulo", "sao paulo"),
        ("revenue in saint paul", "revenue in sao paulo", "sao paulo"),
        ("sales in rio", "sales in rio de janeiro", "rio de janeiro"),
        ("items in bell horizon", "items in belo horizonte", "belo horizonte"),
        ("products in computer accessories", "products in informatica_acessorios", "informatica_acessorios"),
        ("sales for health and beauty", "sales for beleza_saude", "beleza_saude"),
        ("orders paid with credit card", "orders paid with credit_card", "credit_card"),
        ("warehouses in chicaggo", "warehouses in chicago", "chicago"),
    ]
    
    eval_result = corrector.evaluate_correction_accuracy(benchmark_dataset)
    
    print("\n--- Domain Word Correction Evaluation ---")
    print(f"Total Cases:         {eval_result['total_test_cases']}")
    print(f"Accuracy Before:     {eval_result['accuracy_before']}%")
    print(f"Accuracy After:      {eval_result['accuracy_after']}%")
    print(f"Accuracy Gain:       +{eval_result['accuracy_improvement']}%")
    
    assert eval_result["accuracy_before"] <= 30.0, "Before correction, raw misheard text should have low canonical match"
    assert eval_result["accuracy_after"] >= 85.0, "After correction, canonical accuracy should be >= 85%"
    assert eval_result["accuracy_improvement"] > 50.0

def test_multisource_router(setup_phase3):
    """Verify MultiSourceRouter dispatches questions to the correct database engine."""
    db_mgr = setup_phase3["db_mgr"]
    profiles = setup_phase3["profiles"]
    router = MultiSourceRouter(db_mgr)
    
    # 1. Olist questions
    assert router.route_query("Which products brought in the most revenue last quarter?", profiles) == "olist"
    assert router.route_query("How many customers in sao paulo bought electronics?", profiles) == "olist"
    assert router.route_query("What is the total revenue by product category?", profiles) == "olist"

    # Detailed routing inspection
    detailed = router.route_query_detailed("What is the total revenue by product category?", profiles)
    assert detailed["source"] == "olist"
    assert "olist" in detailed["scores"]
    assert len(detailed["matched_terms"]) > 0
    
    # 2. Inventory secondary DB questions
    assert router.route_query("How many units of gaming laptops are in the Chicago warehouse?", profiles) == "inventory"
    assert router.route_query("Show all suppliers with rating above 4.5", profiles) == "inventory"
    
    # 3. CSV questions
    assert router.route_query("What was the commission rate for Alice Cooper?", profiles) == "sales_csv"
    assert router.route_query("Show actual sales versus target sales for sales reps", profiles) == "sales_csv"

def test_schema_linker_pruning_and_bridge(setup_phase3):
    """Verify SchemaLinker selects relevant tables and adds foreign-key bridges."""
    olist_profile = setup_phase3["profiles"]["olist"]
    linker = SchemaLinker(olist_profile)
    
    # Query 1: Revenue by product
    res1 = linker.link_schema("Which products brought in the most revenue?")
    selected1 = res1["selected_tables"]
    assert "order_items" in selected1
    assert "products" in selected1
    assert len(selected1) <= 4
    assert "TABLE: order_items" in res1["schema_prompt"]
    assert "TABLE: products" in res1["schema_prompt"]
    
    # Query 2: Customers in city and order status
    res2 = linker.link_schema("Show delivered orders for customers in sao paulo")
    selected2 = res2["selected_tables"]
    assert "orders" in selected2
    assert "customers" in selected2
    
    # Query 3: Foreign key bridge test (order_items links products to orders)
    res3 = linker.link_schema("Total revenue for products ordered in March")
    selected3 = res3["selected_tables"]
    assert "order_items" in selected3  # Order items has price and connects products to orders


def test_top_customers_by_spend_links_payment_tables_and_routes_to_olist(setup_phase3):
    """'top 10 customers ranked by total spend' must route to olist and link customers, orders, and order_payments."""
    db_mgr = setup_phase3["db_mgr"]
    profiles = setup_phase3["profiles"]
    router = MultiSourceRouter(db_mgr)
    linker = SchemaLinker(profiles["olist"])

    query = "top 10 customers ranked by total spend"
    assert router.route_query(query, profiles) == "olist"

    linked = linker.link_schema(query)
    selected = set(linked["selected_tables"])
    assert {"customers", "orders", "order_payments"}.issubset(selected)
    assert "TABLE: customers" in linked["schema_prompt"]
    assert "TABLE: orders" in linked["schema_prompt"]
    assert "TABLE: order_payments" in linked["schema_prompt"]
