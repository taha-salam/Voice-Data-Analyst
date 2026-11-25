"""
Dataset seeder and importer for Olist Brazilian E-Commerce and secondary data sources.
Supports importing existing Kaggle CSVs or generating rich, realistic mock data.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import random
from datetime import datetime, timedelta

def seed_olist_database(db_path: Path, num_orders: int = 1200):
    """Creates/populates the Olist Brazilian E-commerce SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='orders'")
    if cursor.fetchone()[0] > 0:
        cursor.execute("SELECT count(*) FROM orders")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"Olist database already seeded with {count} orders at {db_path}")
            conn.close()
            return

    print("Generating Olist Brazilian E-commerce dataset...")
    random.seed(42)
    np.random.seed(42)

    # 1. Product Categories & Translations
    categories = [
        ("beleza_saude", "health_beauty"),
        ("informatica_acessorios", "computers_accessories"),
        ("cama_mesa_banho", "bed_bath_table"),
        ("esporte_lazer", "sports_leisure"),
        ("moveis_decoracao", "furniture_decor"),
        ("utilidades_domesticas", "housewares"),
        ("relogios_presentes", "watches_gifts"),
        ("telefonia", "telephony"),
        ("automotivo", "auto"),
        ("brinquedos", "toys"),
        ("eletronicos", "electronics"),
        ("livros_interesse_geral", "books_general_interest"),
        ("perfumaria", "perfumery"),
        ("ferramentas_jardim", "garden_tools"),
        ("pet_shop", "pet_shop")
    ]
    df_translation = pd.DataFrame(categories, columns=["product_category_name", "product_category_name_english"])
    df_translation.to_sql("product_category_name_translation", conn, if_exists="replace", index=False)

    # 2. Cities and States
    cities = [
        ("sao paulo", "SP", "01000"),
        ("rio de janeiro", "RJ", "20000"),
        ("belo horizonte", "MG", "30000"),
        ("brasilia", "DF", "70000"),
        ("curitiba", "PR", "80000"),
        ("porto alegre", "RS", "90000"),
        ("salvador", "BA", "40000"),
        ("campinas", "SP", "13000"),
        ("recife", "PE", "50000"),
        ("fortaleza", "CE", "60000"),
        ("goiania", "GO", "74000"),
        ("florianopolis", "SC", "88000")
    ]

    # 3. Customers
    num_customers = 500
    customer_ids = [f"c_{i:05d}" for i in range(1, num_customers + 1)]
    cust_data = []
    for cid in customer_ids:
        city_info = random.choice(cities)
        cust_data.append({
            "customer_id": cid,
            "customer_unique_id": f"u_{random.randint(10000, 99999)}",
            "customer_zip_code_prefix": city_info[2],
            "customer_city": city_info[0],
            "customer_state": city_info[1]
        })
    df_customers = pd.DataFrame(cust_data)
    df_customers.to_sql("customers", conn, if_exists="replace", index=False)

    # 4. Sellers
    num_sellers = 60
    seller_ids = [f"s_{i:04d}" for i in range(1, num_sellers + 1)]
    seller_data = []
    for sid in seller_ids:
        city_info = random.choice(cities)
        seller_data.append({
            "seller_id": sid,
            "seller_zip_code_prefix": city_info[2],
            "seller_city": city_info[0],
            "seller_state": city_info[1]
        })
    df_sellers = pd.DataFrame(seller_data)
    df_sellers.to_sql("sellers", conn, if_exists="replace", index=False)

    # 5. Products
    num_products = 200
    product_ids = [f"p_{i:04d}" for i in range(1, num_products + 1)]
    product_data = []
    for pid in product_ids:
        cat = random.choice(categories)[0]
        product_data.append({
            "product_id": pid,
            "product_category_name": cat,
            "product_name_lenght": random.randint(20, 60),
            "product_description_lenght": random.randint(100, 1500),
            "product_photos_qty": random.randint(1, 6),
            "product_weight_g": random.randint(100, 8000),
            "product_length_cm": random.randint(10, 80),
            "product_height_cm": random.randint(5, 50),
            "product_width_cm": random.randint(10, 50)
        })
    df_products = pd.DataFrame(product_data)
    df_products.to_sql("products", conn, if_exists="replace", index=False)

    # 6. Orders
    start_date = datetime(2023, 1, 1)
    order_data = []
    order_items_data = []
    payments_data = []
    reviews_data = []

    statuses = ["delivered"] * 85 + ["shipped"] * 8 + ["canceled"] * 4 + ["invoiced"] * 3
    payment_types = ["credit_card"] * 70 + ["boleto"] * 18 + ["voucher"] * 8 + ["debit_card"] * 4

    for i in range(1, num_orders + 1):
        order_id = f"ord_{i:06d}"
        cust_id = random.choice(customer_ids)
        status = random.choice(statuses)
        purchase_time = start_date + timedelta(
            days=random.randint(0, 600),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        approved_time = purchase_time + timedelta(hours=random.randint(1, 12)) if status != "canceled" else None
        delivered_time = purchase_time + timedelta(days=random.randint(3, 14)) if status == "delivered" else None
        estimated_delivery = purchase_time + timedelta(days=random.randint(10, 20))

        order_data.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "order_status": status,
            "order_purchase_timestamp": purchase_time.strftime("%Y-%m-%d %H:%M:%S"),
            "order_approved_at": approved_time.strftime("%Y-%m-%d %H:%M:%S") if approved_time else None,
            "order_delivered_customer_date": delivered_time.strftime("%Y-%m-%d %H:%M:%S") if delivered_time else None,
            "order_estimated_delivery_date": estimated_delivery.strftime("%Y-%m-%d %H:%M:%S")
        })

        # Order Items (1 to 3 items per order)
        items_count = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
        total_order_val = 0.0

        for item_idx in range(1, items_count + 1):
            p_id = random.choice(product_ids)
            s_id = random.choice(seller_ids)
            price = round(float(np.random.exponential(scale=75.0) + 12.0), 2)
            freight = round(float(np.random.uniform(8.0, 35.0)), 2)
            total_order_val += price + freight

            order_items_data.append({
                "order_id": order_id,
                "order_item_id": item_idx,
                "product_id": p_id,
                "seller_id": s_id,
                "shipping_limit_date": (purchase_time + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "price": price,
                "freight_value": freight
            })

        # Payment
        p_type = random.choice(payment_types)
        payments_data.append({
            "order_id": order_id,
            "payment_sequential": 1,
            "payment_type": p_type,
            "payment_installments": random.randint(1, 8) if p_type == "credit_card" else 1,
            "payment_value": round(total_order_val, 2)
        })

        # Review
        reviews_data.append({
            "review_id": f"rev_{i:06d}",
            "order_id": order_id,
            "review_score": random.choices([5, 4, 3, 2, 1], weights=[0.55, 0.22, 0.09, 0.05, 0.09])[0],
            "review_comment_message": "Produto excelente e entrega rapida" if random.random() > 0.6 else None,
            "review_creation_date": (purchase_time + timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S")
        })

    pd.DataFrame(order_data).to_sql("orders", conn, if_exists="replace", index=False)
    pd.DataFrame(order_items_data).to_sql("order_items", conn, if_exists="replace", index=False)
    pd.DataFrame(payments_data).to_sql("order_payments", conn, if_exists="replace", index=False)
    pd.DataFrame(reviews_data).to_sql("order_reviews", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()
    print(f"Olist database created successfully at {db_path} with {len(order_data)} orders!")


def seed_secondary_database(db_path: Path):
    """Creates a secondary SQLite database (Supply Chain & Inventory)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='warehouses'")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    print("Generating secondary database (Warehouse & Inventory)...")
    warehouses = [
        {"warehouse_id": "WH_01", "name": "East Coast Distribution Center", "city": "Boston", "capacity_units": 50000, "manager": "Sarah Jenkins"},
        {"warehouse_id": "WH_02", "name": "Midwest Logistics Hub", "city": "Chicago", "capacity_units": 85000, "manager": "Michael Chang"},
        {"warehouse_id": "WH_03", "name": "West Coast Fulfillment Facility", "city": "Seattle", "capacity_units": 65000, "manager": "Elena Rodriguez"},
        {"warehouse_id": "WH_04", "name": "Southern Regional Depot", "city": "Dallas", "capacity_units": 45000, "manager": "David Miller"}
    ]
    pd.DataFrame(warehouses).to_sql("warehouses", conn, if_exists="replace", index=False)

    suppliers = [
        {"supplier_id": "SUP_001", "supplier_name": "Apex Electronics Ltd", "country": "Taiwan", "rating": 4.8, "lead_time_days": 14},
        {"supplier_id": "SUP_002", "supplier_name": "Nordic Furniture Co", "country": "Sweden", "rating": 4.6, "lead_time_days": 21},
        {"supplier_id": "SUP_003", "supplier_name": "Precision Optics Inc", "country": "Japan", "rating": 4.9, "lead_time_days": 10},
        {"supplier_id": "SUP_004", "supplier_name": "Sun Valley Textiles", "country": "India", "rating": 4.3, "lead_time_days": 30}
    ]
    pd.DataFrame(suppliers).to_sql("suppliers", conn, if_exists="replace", index=False)

    inventory = []
    products = [
        ("p_0001", "Gaming Laptop RTX 4080", "Electronics", 1250.00),
        ("p_0002", "Ergonomic Office Chair", "Furniture", 280.00),
        ("p_0003", "Wireless Noise-Cancelling Headphones", "Audio", 185.00),
        ("p_0004", "Stainless Steel Espresso Machine", "Appliances", 450.00),
        ("p_0005", "4K Ultra-Wide Monitor 34-inch", "Displays", 599.00),
        ("p_0006", "Mechanical Keyboard RGB", "Accessories", 95.00),
        ("p_0007", "Smart Fitness Tracker", "Wearables", 120.00)
    ]

    for p in products:
        for wh in warehouses:
            inventory.append({
                "product_id": p[0],
                "product_name": p[1],
                "category": p[2],
                "unit_cost": p[3],
                "warehouse_id": wh["warehouse_id"],
                "quantity_on_hand": random.randint(15, 600),
                "reorder_level": 50,
                "last_restocked": (datetime.now() - timedelta(days=random.randint(2, 45))).strftime("%Y-%m-%d")
            })

    pd.DataFrame(inventory).to_sql("inventory_stock", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"Secondary database created successfully at {db_path}!")


def seed_sample_csvs(csv_dir: Path):
    """Exports sample CSVs for testing user file uploads."""
    csv_dir.mkdir(parents=True, exist_ok=True)
    sales_reps = [
        {"rep_id": "REP_101", "rep_name": "Alice Cooper", "region": "North", "target_sales": 150000, "actual_sales": 172000, "commission_rate": 0.06},
        {"rep_id": "REP_102", "rep_name": "Bob Dylan", "region": "South", "target_sales": 130000, "actual_sales": 118000, "commission_rate": 0.05},
        {"rep_id": "REP_103", "rep_name": "Charlie Parker", "region": "East", "target_sales": 180000, "actual_sales": 195000, "commission_rate": 0.07},
        {"rep_id": "REP_104", "rep_name": "Diana Ross", "region": "West", "target_sales": 200000, "actual_sales": 240000, "commission_rate": 0.08}
    ]
    pd.DataFrame(sales_reps).to_csv(csv_dir / "sales_representatives.csv", index=False)
    print(f"Sample CSV saved at {csv_dir / 'sales_representatives.csv'}")

if __name__ == "__main__":
    from src.config import Config
    Config.ensure_directories()
    seed_olist_database(Config.OLIST_DB_PATH)
    seed_secondary_database(Config.SECONDARY_DB_PATH)
    seed_sample_csvs(Config.DATA_DIR / "sample_csvs")
