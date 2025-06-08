import sqlite3
import time

DB_FILE = "wow_auctions.db"

# --- CONFIGURATION ---
# You can tweak these settings to find different kinds of deals.
# -----------------------------------------------------------------
# The minimum ratio between the highest and lowest price to be considered a deal.
MIN_PRICE_RATIO = 4.0 # Lowered a bit, as results will be less extreme now

# The minimum price (in gold) for the CHEAPEST version of an item to be included.
MIN_GOLD_PRICE = 1000

# The item must be available on at least this many different realms.
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

def analyze_market_improved():
    """Scans the database using the improved logic to find realistic deals."""
    start_time = time.time()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Starting improved market analysis...")
    
    # This is our new, more advanced query using a Common Table Expression (CTE).
    # STEP 1 (the 'WITH' part): Create a temporary table of the minimum price for each item on each realm.
    # STEP 2 (the 'SELECT' part): Analyze the results from the temporary table.
    summary_query = """
        WITH RealmMinPrices AS (
            SELECT
                item_id,
                connected_realm_id,
                MIN(buyout_price) as min_realm_price
            FROM
                auctions
            WHERE
                buyout_price IS NOT NULL
            GROUP BY
                item_id, connected_realm_id
        )
        SELECT
            item_id,
            MIN(min_realm_price) as overall_min_price,
            MAX(min_realm_price) as overall_max_price,
            COUNT(connected_realm_id) as realm_count
        FROM
            RealmMinPrices
        GROUP BY
            item_id;
    """
    cursor.execute(summary_query)
    item_summaries = cursor.fetchall()
    
    print(f"Found {len(item_summaries)} unique items to analyze.")
    print("Filtering for significant deals based on your refined criteria...")

    potential_deals = []
    for item_id, min_price, max_price, realm_count in item_summaries:
        # Apply our filters
        if realm_count < MIN_REALM_COUNT:
            continue
        if min_price < (MIN_GOLD_PRICE * 10000):
            continue
        
        ratio = max_price / min_price if min_price > 0 else 0
        
        if ratio >= MIN_PRICE_RATIO:
            potential_deals.append({
                "item_id": item_id,
                "min_price": min_price,
                "max_price": max_price,
                "ratio": ratio,
            })

    print(f"Found {len(potential_deals)} potential deals. Fetching realm details...")

    final_deals = []
    # This part can be slow if there are many deals, we can optimize later if needed
    for deal in potential_deals:
        # For each deal, find which realm has the min and max price from our list of minimums
        cursor.execute("SELECT connected_realm_id FROM auctions WHERE item_id = ? AND buyout_price = ? LIMIT 1", (deal['item_id'], deal['min_price']))
        min_realm_result = cursor.fetchone()
        
        cursor.execute("SELECT connected_realm_id FROM auctions WHERE item_id = ? AND buyout_price = ? LIMIT 1", (deal['item_id'], deal['max_price']))
        max_realm_result = cursor.fetchone()
        
        # It's possible for a realm to not be found if the data changes, so we check
        if min_realm_result and max_realm_result:
            deal['min_realm'] = min_realm_result[0]
            deal['max_realm'] = max_realm_result[0]
            final_deals.append(deal)

    # Sort deals by the highest ratio first
    final_deals.sort(key=lambda x: x['ratio'], reverse=True)

    end_time = time.time()
    print(f"\nAnalysis complete in {end_time - start_time:.2f} seconds.")
    print("-" * 70)
    print(f"Top {min(len(final_deals), DEAL_REPORT_LIMIT)} More Realistic Market Opportunities")
    print("-" * 70)

    for deal in final_deals[:DEAL_REPORT_LIMIT]:
        print(f"Item ID: {deal['item_id']:<8} | Ratio: {deal['ratio']:.2f}x")
        print(f"  -> Cheapest Realm Low: {format_price(deal['min_price']):<18} (Realm {deal['min_realm']})")
        print(f"  -> Highest Realm Low:  {format_price(deal['max_price']):<18} (Realm {deal['max_realm']})")
        print("-" * 70)
        
    conn.close()


if __name__ == "__main__":
    analyze_market_improved()