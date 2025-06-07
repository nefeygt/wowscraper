import sqlite3

# The name of our database file.
DB_FILE = "wow_auctions.db"

# SQL command to create our table.
# We use "IF NOT EXISTS" so we can run this script multiple times without error.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY,         -- Unique ID for each auction listing
    item_id INTEGER NOT NULL,       -- The ID of the item being sold
    connected_realm_id INTEGER NOT NULL, -- The realm ID where the auction is
    buyout_price INTEGER,           -- The buyout price in total copper (can be NULL for bids)
    quantity INTEGER NOT NULL,      -- The stack size of the auction
    time_left TEXT NOT NULL,        -- e.g., "SHORT", "LONG"
    scan_timestamp DATETIME NOT NULL -- The date and time we scanned this data
);
"""

try:
    # Connect to the database. If the file doesn't exist, it will be created.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"Successfully connected to database file: {DB_FILE}")

    # Execute the SQL command to create the table.
    cursor.execute(CREATE_TABLE_SQL)
    print("'auctions' table created or already exists.")
    
    # Commit the changes and close the connection.
    conn.commit()
    conn.close()

    print("Database setup complete.")

except sqlite3.Error as e:
    print(f"Database error: {e}")