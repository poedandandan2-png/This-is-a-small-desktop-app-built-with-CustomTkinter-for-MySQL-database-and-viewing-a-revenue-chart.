This is a final I did for my business programming class. No Ai was used here.

Connects to a MySQL database on a remote server using SQLAlchemy and PyMySQL.
Creates two tables if they don’t exist:
cjacks20_products (product ID, name, price)
cjacks20_sales (sale ID, product ID, units sold, sales date)
Wipes both tables clean every time the script starts (clear_all_records() truncates them), so no data persists between runs.
Opens a GUI window titled “Sales Data Manager” with a green theme.

The GUI

Four input fields: product name, product price, units sold, and sales date (YYYY-MM-DD).
Save Sale button: inserts the product (or updates its price if the name already exists), looks up its ID, inserts a sales record, then clears the input fields.
Show Sales Graph button: queries total revenue per product (price × units sold, summed) and draws a green bar chart inside the window using matplotlib.
