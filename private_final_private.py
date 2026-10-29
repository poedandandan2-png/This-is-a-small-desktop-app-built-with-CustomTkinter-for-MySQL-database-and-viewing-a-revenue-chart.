import os
import sys
from datetime import datetime

import pymysql
import matplotlib.pyplot as plt
import customtkinter as ctk
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String, DECIMAL, Date
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------------------------------------------------------------------
# Database connection details
# Set these as environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
# so credentials never live in the source file. The REDACTED values below are
# placeholders only and for privacy.
# ---------------------------------------------------------------------------
host = os.environ.get("DB_HOST", "REDACTED")
user = os.environ.get("DB_USER", "REDACTED")
password = os.environ.get("DB_PASSWORD", "REDACTED")
database = os.environ.get("DB_NAME", "REDACTED")

# Original behavior wiped both tables on every start. Set to False to keep data.
CLEAR_ON_START = True

# ---------------------------------------------------------------------------
# Create the tables if they don't exist
# ---------------------------------------------------------------------------
try:
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}")
    metadata = MetaData()

    # productName is UNIQUE so ON DUPLICATE KEY UPDATE actually works
    products_table = Table(
        "cjacks20_products", metadata,
        Column("productID", Integer, primary_key=True, autoincrement=True),
        Column("productName", String(45), nullable=False, unique=True),
        Column("productPrice", DECIMAL(8, 2), nullable=False),
    )
    sales_table = Table(
        "cjacks20_sales", metadata,
        Column("PK", Integer, primary_key=True, autoincrement=True),
        Column("productID", Integer, nullable=False),
        Column("unitSales", Integer, nullable=False),
        Column("salesDate", Date, nullable=False),
    )

    existing_tables = inspect(engine).get_table_names()
    if "cjacks20_products" not in existing_tables:
        print("cjacks20_products table does not exist. Creating table...")
        products_table.create(engine)
    if "cjacks20_sales" not in existing_tables:
        print("cjacks20_sales table does not exist. Creating table...")
        sales_table.create(engine)
    print("Tables are ready")
except Exception as e:
    print(f"Error setting up tables: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Connect for queries
# ---------------------------------------------------------------------------
try:
    conn = pymysql.connect(host=host, user=user, password=password, database=database)
    cursor = conn.cursor()
    print("Connected to the database successfully.")
except Exception as e:
    print(f"Database connection error: {e}")
    sys.exit(1)


def clear_all_records():
    """Remove all records from both tables."""
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE cjacks20_sales")
        cursor.execute("TRUNCATE TABLE cjacks20_products")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("All records cleared successfully.")
    except Exception as e:
        print(f"Error clearing records: {e}")


def ensure_unique_product_name():
    """If the table was created by an older version of this script, add the
    missing UNIQUE constraint on productName (safe to run repeatedly)."""
    try:
        cursor.execute("SHOW INDEX FROM cjacks20_products WHERE Column_name = 'productName' AND Non_unique = 0")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE cjacks20_products ADD UNIQUE (productName)")
            conn.commit()
            print("Added UNIQUE constraint to productName.")
    except Exception as e:
        print(f"Could not add UNIQUE constraint (duplicate product names may exist): {e}")


if CLEAR_ON_START:
    clear_all_records()
ensure_unique_product_name()

# ---------------------------------------------------------------------------
# GUI setup
# ---------------------------------------------------------------------------
ctk.set_default_color_theme("green")
ctk.set_appearance_mode("system")

window = ctk.CTk()
window.geometry("900x750")
window.title("Sales Data Manager")


def set_status(message, is_error=False):
    """Show feedback in the GUI instead of only the console."""
    status_label.configure(text=message, text_color="red" if is_error else "green")
    print(message)


def save_sale():
    try:
        product_name = product_name_input.get().strip()
        if not product_name:
            raise ValueError("Product name is required.")
        product_price = float(product_price_input.get())
        units_sold = int(units_sold_input.get())
        sales_date = sales_date_input.get().strip()
        # Validate date format before it reaches the database
        datetime.strptime(sales_date, "%Y-%m-%d")

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cjacks20_products (productName, productPrice)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE productPrice = VALUES(productPrice)
            """,
            (product_name, product_price),
        )

        cur.execute("SELECT productID FROM cjacks20_products WHERE productName = %s", (product_name,))
        result = cur.fetchone()
        if not result:
            raise ValueError("Product ID retrieval failed.")
        product_id = result[0]

        cur.execute(
            """
            INSERT INTO cjacks20_sales (productID, unitSales, salesDate)
            VALUES (%s, %s, %s)
            """,
            (product_id, units_sold, sales_date),
        )
        conn.commit()

        for entry in (product_name_input, product_price_input, units_sold_input, sales_date_input):
            entry.delete(0, ctk.END)
        set_status("Sale data saved successfully.")

    except ValueError as e:
        conn.rollback()
        set_status(f"Invalid input: {e}", is_error=True)
    except Exception as e:
        conn.rollback()
        set_status(f"Error saving sale: {e}", is_error=True)


def show_sales_graph():
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.productName, SUM(p.productPrice * s.unitSales) AS totalRevenue
            FROM cjacks20_products p
            JOIN cjacks20_sales s ON p.productID = s.productID
            GROUP BY p.productName
            """
        )
        data = cur.fetchall()
        if not data:
            set_status("No sales data to graph yet.", is_error=True)
            return

        product_names = [row[0] for row in data]
        revenues = [float(row[1]) for row in data]

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(product_names, revenues, color="lightgreen")
        ax.set_title("Total Sales Revenue by Product")
        ax.set_xlabel("Product Name")
        ax.set_ylabel("Total Revenue ($)")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()

        for widget in frame_graph.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame_graph)
        canvas.draw()
        canvas.get_tk_widget().pack()
        plt.close(fig)  # free the figure so repeated clicks don't leak memory
        set_status("Graph updated.")

    except Exception as e:
        set_status(f"Error generating graph: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
ctk.CTkLabel(window, text="Product Name:").grid(row=0, column=0, padx=25, pady=5, sticky="w")
ctk.CTkLabel(window, text="Product Price:").grid(row=1, column=0, padx=25, pady=5, sticky="w")
ctk.CTkLabel(window, text="Units Sold (don't add , ):").grid(row=2, column=0, padx=25, pady=5, sticky="w")
ctk.CTkLabel(window, text="Sales Date (YYYY-MM-DD):").grid(row=3, column=0, padx=25, pady=5, sticky="w")

product_name_input = ctk.CTkEntry(window)
product_name_input.grid(row=0, column=1, padx=25, pady=5)
product_price_input = ctk.CTkEntry(window)
product_price_input.grid(row=1, column=1, padx=25, pady=5)
units_sold_input = ctk.CTkEntry(window)
units_sold_input.grid(row=2, column=1, padx=25, pady=5)
sales_date_input = ctk.CTkEntry(window)
sales_date_input.grid(row=3, column=1, padx=25, pady=5)

ctk.CTkButton(window, text="Save Sale", command=save_sale).grid(row=4, column=0, padx=25, pady=5)
ctk.CTkButton(window, text="Show Sales Graph", command=show_sales_graph).grid(row=4, column=1, padx=25, pady=5)

status_label = ctk.CTkLabel(window, text="")
status_label.grid(row=5, column=0, columnspan=2, padx=25, pady=5)

frame_graph = ctk.CTkFrame(window)
frame_graph.grid(row=6, column=0, columnspan=2, pady=10, padx=25)

window.mainloop()

conn.close()
