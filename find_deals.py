import sqlite3
import time
import numpy as np

DB_FILE = "wow_auctions.db"

# --- CONFIGURATION ---
# The minimum ratio between the realistic highest and lowest price.
MIN_PRICE_RATIO = 3.0

# The minimum price (in gold) for the CHEAPEST version of an item to be included.
MIN_GOLD_PRICE = 1000

# The item must be available on at least this many different realms AFTER cleaning outliers.
MIN_REALM_COUNT = 5

# How many top deals do you want to see in the final report?
DEAL_REPORT_LIMIT = 25
# -----------------------------------------------------------------


def format_price(price_in_copper):
    """Converts a copper value into a readable gold, silver, copper string."""
    if not isinstance(price_in_copper, (int, float)): return "N/A"
    gold = int(price_in_copper / 10000)
    silver = int((price_in_copper % 10000) / 100)
    copper = int(price_in_copper % 100)
    return f"{gold}g {silver}s {copper}c"

def analyze_market_final():
    """Scans the database using statistical outlier rejection to find the best deals."""
    start_time = time.time()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Starting final market analysis with statistical outlier rejection...")
    
    # Step 1: Get the minimum price for each item on each realm. This is our raw data.
    raw_prices_query = """
        SELECT
            item_id,
            MIN(buyout_price) as min_realm_price
        FROM
            auctions
        WHERE
            buyout_price IS NOT NULL
        GROUP BY
            item_id, connected_realm_id;
    """
    cursor.execute(raw_prices_query)
    
    # Group all the minimum prices by item_id in a dictionary
    item_prices = {}
    for item_id, price in cursor.fetchall():
        if item_id not in item_prices:
            item_prices[item_id] = []
        item_prices[item_id].append(price)

    print(f"Found {len(item_prices)} unique items. Applying statistical analysis...")

    potential_deals = []
    for item_id, prices in item_prices.items():
        # Ensure we have enough data points to do meaningful stats
        if len(prices) < MIN_REALM_COUNT:
            continue

        prices_array = np.array(prices)
        
        # Step 2: Calculate statistical properties to find outliers
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1
        
        # Define the upper limit for a price to be considered "realistic"
        # Any price above this is considered a statistical outlier
        outlier_threshold = q3 + (1.5 * iqr)
        
        # Step 3: Filter out the outliers
        realistic_prices = prices_array[prices_array <= outlier_threshold]

        # Check if we still have enough data after cleaning
        if len(realistic_prices) < MIN_REALM_COUNT:
            continue
        
        # Step 4: Get the min and max from the CLEANED data
        min_realistic_price = np.min(realistic_prices)
        max_realistic_price = np.max(realistic_prices)

        # Apply our filters to the cleaned data
        if min_realistic_price < (MIN_GOLD_PRICE * 10000):
            continue

        ratio = max_realistic_price / min_realistic_price if min_realistic_price > 0 else 0

        if ratio >= MIN_PRICE_RATIO:
            potential_deals.append({
                "item_id": item_id,
                "min_price": min_realistic_price,
                "max_price": max_realistic_price,
                "ratio": ratio,
            })

    print(f"Found {len(potential_deals)} potential deals after cleaning. Fetching realm details...")

    # Fetch realm details for our finalized deals
    final_deals = []
    for deal in potential_deals:
        cursor.execute("SELECT connected_realm_id FROM auctions WHERE item_id = ? AND buyout_price = ? LIMIT 1", (deal['item_id'], deal['min_price']))
        min_realm_result = cursor.fetchone()
        
        cursor.execute("SELECT connected_realm_id FROM auctions WHERE item_id = ? AND buyout_price = ? LIMIT 1", (deal['item_id'], deal['max_price']))
        max_realm_result = cursor.fetchone()
        
        if min_realm_result and max_realm_result:
            deal['min_realm'] = min_realm_result[0]
            deal['max_realm'] = max_realm_result[0]
            final_deals.append(deal)

    final_deals.sort(key=lambda x: x['ratio'], reverse=True)
    end_time = time.time()
    print(f"\nAnalysis complete in {end_time - start_time:.2f} seconds.")
    print("-" * 70)
    print(f"Top {min(len(final_deals), DEAL_REPORT_LIMIT)} Statistically Significant Market Opportunities")
    print("-" * 70)

    for deal in final_deals[:DEAL_REPORT_LIMIT]:
        print(f"Item ID: {deal['item_id']:<8} | Ratio: {deal['ratio']:.2f}x")
        print(f"  -> Cheapest Realm Low: {format_price(deal['min_price']):<18} (Realm {deal['min_realm']})")
        print(f"  -> Realistic High Low: {format_price(deal['max_price']):<18} (Realm {deal['max_realm']})")
        print("-" * 70)
        
    conn.close()


if __name__ == "__main__":
    analyze_market_final()