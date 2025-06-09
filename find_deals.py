import sqlite3
import time
import numpy as np
from collections import defaultdict

DB_FILE = "wow_auctions.db"

# --- CONFIGURATION ---
MIN_PRICE_RATIO = 3.0
MIN_GOLD_PRICE = 1000
MIN_REALM_COUNT = 5
DEAL_REPORT_LIMIT = 25
MAX_REALISTIC_GOLD_PRICE = 3000000  # Ignore any "max price" above 3 million gold
# -----------------------------------------------------------------


def format_price(price_in_copper):
    """Converts a copper value into a readable gold, silver, copper string."""
    if not isinstance(price_in_copper, (int, float, np.integer)):
        return "N/A"
    gold = int(price_in_copper / 10000)
    silver = int((price_in_copper % 10000) / 100)
    copper = int(price_in_copper % 100)
    return f"{gold}g {silver}s {copper}c"


def analyze_market_optimized():
    """Optimized version that processes data in-memory to avoid slow lookups."""
    start_time = time.time()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Starting optimized market analysis...")

    # Step 1: Fetch all necessary data at once.
    # We get a list of (item, realm, price) for every realm's minimum.
    raw_prices_query = """
        SELECT
            item_id,
            connected_realm_id,
            MIN(buyout_price) as min_realm_price
        FROM
            auctions
        WHERE
            buyout_price IS NOT NULL
        GROUP BY
            item_id, connected_realm_id;
    """
    cursor.execute(raw_prices_query)
    all_realm_min_prices = cursor.fetchall()
    conn.close()  # We are done with the database now.

    # Step 2: Group the data by item_id in a dictionary for easy processing.
    # The structure will be: {item_id: [(price, realm_id), (price, realm_id), ...]}
    item_data = defaultdict(list)
    for item_id, realm_id, price in all_realm_min_prices:
        item_data[item_id].append((price, realm_id))

    print(f"Found {len(item_data)} unique items. Applying statistical analysis in-memory...")

    final_deals = []
    for item_id, price_realm_tuples in item_data.items():
        # Ensure we have enough data points for meaningful analysis
        if len(price_realm_tuples) < MIN_REALM_COUNT:
            continue

        prices_array = np.array([t[0] for t in price_realm_tuples])

        # Step 3: Perform statistical outlier rejection (IQR-based)
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1
        outlier_threshold = q3 + (1.5 * iqr)

        # Create a new list of (price, realm) tuples without IQR outliers
        realistic_data = [t for t in price_realm_tuples if t[0] <= outlier_threshold]

        # Additional median-based filter
        if realistic_data:
            median_price = np.median([t[0] for t in realistic_data])
            mad = np.median(np.abs([t[0] for t in realistic_data] - median_price)) or 1
            mad_threshold = 5 * mad
            realistic_data = [
                t for t in realistic_data
                if abs(t[0] - median_price) <= mad_threshold
            ]

        if len(realistic_data) < MIN_REALM_COUNT:
            continue

        # Step 4: Find the min and max from the CLEANED data
        realistic_data.sort(key=lambda x: x[0])
        min_price, min_realm = realistic_data[0]
        max_price, max_realm = realistic_data[-1]

        # Apply final filters
        if min_price < (MIN_GOLD_PRICE * 10000):
            continue

        ratio = max_price / min_price if min_price > 0 else 0

        # Final hard cap to filter extreme outliers
        if max_price > (MAX_REALISTIC_GOLD_PRICE * 10000):
            continue

        if ratio >= MIN_PRICE_RATIO:
            final_deals.append({
                "item_id": item_id,
                "min_price": min_price,
                "max_price": max_price,
                "min_realm": min_realm,
                "max_realm": max_realm,
                "ratio": ratio,
            })

    # Sort the final list by the most profitable ratio
    final_deals.sort(key=lambda x: x['ratio'], reverse=True)
    end_time = time.time()

    # Step 5: Print the final report
    print(f"\nAnalysis complete in {end_time - start_time:.2f} seconds.")
    print("-" * 70)
    print(f"Top {min(len(final_deals), DEAL_REPORT_LIMIT)} Statistically Significant Market Opportunities")
    print("-" * 70)

    if not final_deals:
        print("No deals found matching your criteria. Try adjusting the CONFIG settings.")

    for deal in final_deals[:DEAL_REPORT_LIMIT]:
        print(f"Item ID: {deal['item_id']:<8} | Ratio: {deal['ratio']:.2f}x")
        print(f"  -> Cheapest Realm Low: {format_price(deal['min_price']):<18} (Realm {deal['min_realm']})")
        print(f"  -> Realistic High Low: {format_price(deal['max_price']):<18} (Realm {deal['max_realm']})")
        print("-" * 70)


if __name__ == "__main__":
    analyze_market_optimized()