from flask import Flask, jsonify, render_template, request
import sqlite3
import time
import numpy as np
from collections import defaultdict

app = Flask(__name__)

# --- Configuration ---
DB_FILE = "wow_auctions.db"
MIN_PRICE_RATIO = 3.0
MIN_GOLD_PRICE = 1000
MAX_REALISTIC_GOLD_PRICE = 3000000
MIN_REALM_COUNT = 5
PAGE_SIZE = 25
# ----------------------

def format_price(price_in_copper):
    if not isinstance(price_in_copper, (int, float, np.integer)):
        return "N/A"
    gold = int(price_in_copper / 10000)
    silver = int((price_in_copper % 10000) / 100)
    copper = int(price_in_copper % 100)
    return f"{gold}g {silver}s {copper}c"

def get_deals_page(page=1, page_size=25):
    offset = (page - 1) * page_size
    start_time = time.time()

    try:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        cursor = conn.cursor()
        raw_prices_query = """
            SELECT item_id, connected_realm_id, MIN(buyout_price)
            FROM auctions
            WHERE buyout_price IS NOT NULL
            GROUP BY item_id, connected_realm_id;
        """
        cursor.execute(raw_prices_query)
        all_realm_min_prices = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

    item_data = defaultdict(list)
    for item_id, realm_id, price in all_realm_min_prices:
        item_data[item_id].append((price, realm_id))

    deals = []
    for item_id, price_realm_tuples in item_data.items():
        if len(price_realm_tuples) < MIN_REALM_COUNT:
            continue

        prices_array = np.array([p for p, _ in price_realm_tuples])
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1
        outlier_threshold = q3 + (1.5 * iqr)

        realistic_data = [t for t in price_realm_tuples if t[0] <= outlier_threshold]
        if realistic_data:
            median_price = np.median([t[0] for t in realistic_data])
            mad = np.median(np.abs([t[0] - median_price for t in realistic_data])) or 1
            mad_threshold = 5 * mad
            realistic_data = [
                t for t in realistic_data
                if abs(t[0] - median_price) <= mad_threshold
            ]

        if len(realistic_data) < MIN_REALM_COUNT:
            continue

        realistic_data.sort(key=lambda x: x[0])
        min_price, min_realm = realistic_data[0]
        max_price, max_realm = realistic_data[-1]

        if min_price < (MIN_GOLD_PRICE * 10000) or max_price > (MAX_REALISTIC_GOLD_PRICE * 10000):
            continue

        ratio = max_price / min_price
        if ratio < MIN_PRICE_RATIO:
            continue

        deals.append((item_id, ratio, min_price, min_realm, max_price, max_realm))

    deals.sort(key=lambda x: x[1], reverse=True)
    selected_deals = deals[offset:offset + page_size]

    try:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        cursor = conn.cursor()
        final_results = []
        for item_id, ratio, min_price, min_realm, max_price, max_realm in selected_deals:
            cursor.execute("SELECT name, icon_url FROM items WHERE item_id = ?", (item_id,))
            item_row = cursor.fetchone()
            item_name, icon_url = item_row if item_row else ("Unknown", "")

            cursor.execute("SELECT name FROM realms WHERE connected_realm_id = ?", (min_realm,))
            min_realm_name_row = cursor.fetchone()
            min_realm_name = min_realm_name_row[0] if min_realm_name_row else str(min_realm)

            cursor.execute("SELECT name FROM realms WHERE connected_realm_id = ?", (max_realm,))
            max_realm_name_row = cursor.fetchone()
            max_realm_name = max_realm_name_row[0] if max_realm_name_row else str(max_realm)

            final_results.append({
                "itemId": item_id,
                "itemName": item_name,
                "itemIcon": icon_url,
                "minPrice": format_price(min_price),
                "maxPrice": format_price(max_price),
                "minRealm": min_realm_name,
                "maxRealm": max_realm_name,
                "ratio": f"{ratio:.2f}x"
            })
        return final_results
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/deals')
def get_deals():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    deals = get_deals_page(page)
    return jsonify(deals)

if __name__ == '__main__':
    app.run(debug=True)