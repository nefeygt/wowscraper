from dotenv import load_dotenv
import os
import requests
import sqlite3
from datetime import datetime
import time

load_dotenv()

# --- Configuration ---
client_id = 'a446f3e402fb474eaeeab49a4ace4fe4'
client_secret = os.getenv("SECRET_KEY") # Replace with your secret
region = 'eu'
namespace = f'dynamic-{region}'
STATIC_NAMESPACE = f'static-{region}' # For item data
locale = 'en_US'
DB_FILE = "wow_auctions.db"

def get_access_token():
    """Gets an access token from the Blizzard API."""
    token_url = f'https://{region}.oauth.battle.net/token'
    payload = {'grant_type': 'client_credentials'}
    try:
        response = requests.post(token_url, data=payload, auth=(client_id, client_secret))
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as err:
        print(f"Error obtaining token: {err}")
        return None

def get_all_realm_ids(token):
    """Gets a list of all connected realm IDs."""
    realms_url = f'https://{region}.api.blizzard.com/data/wow/connected-realm/index'
    headers = {'Authorization': f'Bearer {token}', 'Battlenet-Namespace': namespace}
    params = {'locale': locale}
    try:
        response = requests.get(realms_url, headers=headers, params=params)
        response.raise_for_status()
        realms_data = response.json().get('connected_realms', [])
        # Extract the ID from the href URL for each realm
        return [int(realm['href'].split('/')[-1].split('?')[0]) for realm in realms_data]
    except requests.exceptions.RequestException as err:
        print(f"Error fetching realms: {err}")
        return []

def get_item_details(item_id, access_token):
    """Fetches item name, quality, and icon URL from Blizzard API."""
    item_info_url = f'https://{region}.api.blizzard.com/data/wow/item/{item_id}'
    item_media_url = f'https://{region}.api.blizzard.com/data/wow/media/item/{item_id}'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Battlenet-Namespace': STATIC_NAMESPACE # Use static namespace for item data
    }
    params = {'locale': locale}

    item_name = "Unknown Item"
    item_quality = "COMMON" # Default quality
    icon_url = ""

    try:
        # Get item name and quality
        response_info = requests.get(item_info_url, headers=headers, params=params)
        if response_info.status_code == 200:
            data_info = response_info.json()
            item_name = data_info.get('name', item_name)
            item_quality_data = data_info.get('quality', {})
            item_quality = item_quality_data.get('type', item_quality).upper()
        else:
            print(f"Warning: Could not fetch item info for {item_id}. Status: {response_info.status_code}, Response: {response_info.text[:200]}")

        # Get item icon
        response_media = requests.get(item_media_url, headers=headers, params=params)
        if response_media.status_code == 200:
            data_media = response_media.json()
            if 'assets' in data_media and data_media['assets']:
                for asset in data_media['assets']:
                    if asset.get('key') == 'icon':
                        icon_url = asset.get('value', '')
                        break
            # Fallback for some items that might have icon directly (less common with current API)
            elif 'icon' in data_media:
                 icon_url = data_media.get('icon', '')
        else:
            print(f"Warning: Could not fetch item media for {item_id}. Status: {response_media.status_code}, Response: {response_media.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for item {item_id}: {e}")
    except Exception as e: # Catch other potential errors like JSONDecodeError
        print(f"Unexpected error processing item {item_id}: {e}")
        # You might want to see the response text if JSON decoding fails
        if 'response_info' in locals() and response_info.status_code != 200:
            print(f"Item info response text: {response_info.text[:200]}")
        if 'response_media' in locals() and response_media.status_code != 200:
            print(f"Item media response text: {response_media.text[:200]}")

    return item_name, item_quality, icon_url

def main():
    print("Starting the WoW Auction House Scanner...")
    
    access_token = get_access_token()
    if not access_token:
        return

    print("Successfully obtained access token.")

    realm_ids = get_all_realm_ids(access_token)
    if not realm_ids:
        print("Could not retrieve realm list. Exiting.")
        return
    
    total_realms = len(realm_ids)
    print(f"Found {total_realms} connected realms to scan.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("Connected to database. Clearing old auction data...")
    cursor.execute("DELETE FROM auctions")
    conn.commit()
    print("Old data cleared.")

    # Load existing item IDs from the items table to avoid re-fetching known items
    processed_item_ids = set()
    try:
        cursor.execute("SELECT item_id FROM items")
        for row in cursor.fetchall():
            processed_item_ids.add(row[0])
        print(f"Loaded {len(processed_item_ids)} existing item IDs from item cache.")
    except sqlite3.Error as e:
        print(f"Could not load existing items, will fetch all: {e}")


    for i, realm_id in enumerate(realm_ids):
        print(f"\n[{i+1}/{total_realms}] Scanning Realm ID: {realm_id}...")
        
        try:
            auctions_url = f'https://{region}.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions'
            # Ensure correct namespace for auction calls
            headers_auctions = {'Authorization': f'Bearer {access_token}', 'Battlenet-Namespace': namespace}
            auctions_response = requests.get(auctions_url, headers=headers_auctions)
            auctions_response.raise_for_status()
            
            auctions_data = auctions_response.json().get('auctions', [])
            print(f"Found {len(auctions_data)} auctions.")
            
            if not auctions_data:
                print("No auctions found for this realm, skipping.")
                continue

            scan_time = datetime.now()
            auctions_to_insert = []
            items_to_cache_in_this_batch = [] # Items to add/update in the items table

            unique_item_ids_in_batch = set()
            for auction in auctions_data:
                unique_item_ids_in_batch.add(auction['item']['id'])

            for item_id_from_auction in unique_item_ids_in_batch:
                if item_id_from_auction not in processed_item_ids:
                    print(f"New item ID {item_id_from_auction} found. Fetching details...")
                    name, quality, icon = get_item_details(item_id_from_auction, access_token)
                    items_to_cache_in_this_batch.append((item_id_from_auction, name, quality, icon))
                    processed_item_ids.add(item_id_from_auction) # Mark as processed (attempted to fetch)

            # Bulk insert/update item details (IGNORE if item_id already exists)
            if items_to_cache_in_this_batch:
                cursor.executemany(
                    "INSERT OR IGNORE INTO items (item_id, name, quality, icon_url) VALUES (?, ?, ?, ?)",
                    items_to_cache_in_this_batch
                )
                conn.commit() 
                print(f"Cached/updated details for {len(items_to_cache_in_this_batch)} items.")
            
            # Prepare auction data for insertion
            for auction in auctions_data:
                auctions_to_insert.append((
                    auction['id'],
                    auction['item']['id'],
                    realm_id,
                    auction.get('buyout'), 
                    auction['quantity'],
                    auction['time_left'],
                    scan_time
                ))

            # Bulk insert the auction data for this realm
            if auctions_to_insert:
                cursor.executemany(
                    "INSERT INTO auctions (id, item_id, connected_realm_id, buyout_price, quantity, time_left, scan_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    auctions_to_insert
                )
                conn.commit()
                print(f"Successfully saved {len(auctions_to_insert)} auctions to the database.")

        except requests.exceptions.RequestException as err:
            print(f"Could not fetch data for realm {realm_id}. Error: {err}")
            time.sleep(2)
        except sqlite3.Error as err:
            print(f"Database error for realm {realm_id}. Error: {err}")
        except Exception as e:
            print(f"An unexpected error occurred processing realm {realm_id}: {e}")


    conn.close()
    print("\n---------------------------------")
    print("Scanner finished. All realms have been processed.")
    print("Your database 'wow_auctions.db' is now populated with fresh data, including item details.")

if __name__ == "__main__":
    main()