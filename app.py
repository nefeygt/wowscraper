from flask import Flask, jsonify, render_template
import sqlite3
import time
import numpy as np
from collections import defaultdict

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration for the analysis ---
DB_FILE = "wow_auctions.db"
MIN_PRICE_RATIO = 3.0
MIN_GOLD_PRICE = 1000
MAX_REALISTIC_GOLD_PRICE = 3000000 # Hard cap to filter extreme outliers
MIN_REALM_COUNT = 5
DEAL_REPORT_LIMIT = 25
# ------------------------------------

def format_price(price_in_copper):
    """Converts a copper value into a readable gold, silver, copper string."""
    if not isinstance(price_in_copper, (int, float, np.integer)): return "N/A"
    gold = int(price_in_copper / 10000)
    silver = int((price_in_copper % 10000) / 100)
    copper = int(price_in_copper % 100)
    return f"{gold}g {silver}s {copper}c"

def analyze_market_optimized():
    """Optimized analysis function that now returns the list of deals."""
    start_time = time.time()
    try:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True) # Read-only connection
        cursor = conn.cursor()

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
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return [] # Return empty list on error
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    item_data = defaultdict(list)
    for item_id, realm_id, price in all_realm_min_prices:
        item_data[item_id].append((price, realm_id))
    
    final_deals = []
    for item_id, price_realm_tuples in item_data.items():
        if len(price_realm_tuples) < MIN_REALM_COUNT:
            continue

        prices_array = np.array([t[0] for t in price_realm_tuples])
        q1, q3 = np.percentile(prices_array, [25, 75])
        iqr = q3 - q1
        outlier_threshold = q3 + (1.5 * iqr)
        
        realistic_data = [t for t in price_realm_tuples if t[0] <= outlier_threshold]

        if len(realistic_data) < MIN_REALM_COUNT:
            continue
            
        realistic_data.sort(key=lambda x: x[0])
        min_price, min_realm = realistic_data[0]
        max_price, max_realm = realistic_data[-1]

        if min_price < (MIN_GOLD_PRICE * 10000) or max_price > (MAX_REALISTIC_GOLD_PRICE * 10000):
            continue
            
        ratio = max_price / min_price if min_price > 0 else 0
        
        if ratio >= MIN_PRICE_RATIO:
            final_deals.append({
                "itemId": item_id,
                "minPrice": format_price(min_price),
                "maxPrice": format_price(max_price),
                "minRealm": min_realm,
                "maxRealm": max_realm,
                "ratio": f"{ratio:.2f}x",
            })

    final_deals.sort(key=lambda x: float(x['ratio'][:-1]), reverse=True)
    end_time = time.time()
    
    print(f"API Request: Analysis completed in {end_time - start_time:.2f} seconds.")
    
    return final_deals[:DEAL_REPORT_LIMIT]

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/deals')
def get_deals():
    """This is our API endpoint that provides the data."""
    deals = analyze_market_optimized()
    return jsonify(deals)

if __name__ == '__main__':
    app.run(debug=True)