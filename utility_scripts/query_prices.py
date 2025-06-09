import sqlite3
import statistics

DB_FILE = "wow_auctions.db"

def format_price(price_in_copper):
    """Converts a copper value into a readable gold, silver, copper string."""
    if not isinstance(price_in_copper, (int, float)):
        return "N/A"
    
    gold = int(price_in_copper / 10000)
    silver = int((price_in_copper % 10000) / 100)
    copper = int(price_in_copper % 100)
    return f"{gold}g {silver}s {copper}c"

def analyze_item_prices(item_id):
    """Queries the database for a specific item and prints a price analysis."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print(f"\nSearching for Item ID: {item_id}...")

        # Securely query the database using a parameterized query to prevent SQL injection
        query = """
            SELECT
                connected_realm_id,
                buyout_price
            FROM
                auctions
            WHERE
                item_id = ? AND buyout_price IS NOT NULL
            ORDER BY
                buyout_price ASC;
        """
        cursor.execute(query, (item_id,))
        results = cursor.fetchall()

        if not results:
            print(f"-> No active buyout auctions found for Item ID {item_id}.")
            return

        print(f"-> Found {len(results)} active auctions for this item across all realms.")
        print("-" * 40)
        
        # Print each realm and its lowest price
        # (Note: A realm might appear multiple times if there are multiple auctions)
        for realm_id, price in results:
            print(f"  Realm ID: {realm_id:<6} | Price: {format_price(price)}")

        # Perform price analysis
        prices = [row[1] for row in results]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = statistics.mean(prices)
        
        print("-" * 40)
        print("Price Analysis:")
        print(f"  Lowest Price:  {format_price(min_price)}")
        print(f"  Highest Price: {format_price(max_price)}")
        print(f"  Average Price: {format_price(avg_price)}")
        print("-" * 40)


    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        while True:
            user_input = input("Enter the Item ID to search for (or type 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            if user_input.isdigit():
                analyze_item_prices(int(user_input))
            else:
                print("Invalid input. Please enter a number.")
    except KeyboardInterrupt:
        print("\nExiting program.")