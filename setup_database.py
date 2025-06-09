import sqlite3

DB_FILE = "wow_auctions.db"

# SQL command for the main auctions table (unchanged)
CREATE_AUCTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    connected_realm_id INTEGER NOT NULL,
    buyout_price INTEGER,
    quantity INTEGER NOT NULL,
    time_left TEXT NOT NULL,
    scan_timestamp DATETIME NOT NULL
);
"""

# SQL command for items cache table
CREATE_ITEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    quality TEXT NOT NULL,
    icon_url TEXT NOT NULL
);
"""

# SQL command for realms cache table
CREATE_REALMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS realms (
    connected_realm_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
"""


try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"Successfully connected to database file: {DB_FILE}")

    # Execute the SQL commands to create the tables
    cursor.execute(CREATE_AUCTIONS_TABLE_SQL)
    print("'auctions' table checked.")
    cursor.execute(CREATE_ITEMS_TABLE_SQL)
    print("'items' table created or already exists.")
    cursor.execute(CREATE_REALMS_TABLE_SQL)
    print("'realms' table created or already exists.")
    
    conn.commit()
    conn.close()

    print("Database setup complete.")

except sqlite3.Error as e:
    print(f"Database error: {e}")