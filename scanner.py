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

def main():
    print("Starting the WoW Auction House Scanner...")
    
    # 1. Get Access Token
    access_token = get_access_token()
    if not access_token:
        return # Stop if we can't get a token

    print("Successfully obtained access token.")

    # 2. Get All Realm IDs
    realm_ids = get_all_realm_ids(access_token)
    if not realm_ids:
        print("Could not retrieve realm list. Exiting.")
        return
    
    total_realms = len(realm_ids)
    print(f"Found {total_realms} connected realms to scan.")

    # 3. Connect to DB and clear old data
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("Connected to database. Clearing old auction data...")
    cursor.execute("DELETE FROM auctions")
    conn.commit()
    print("Old data cleared.")

    # 4. Loop through each realm and fetch/store auction data
    for i, realm_id in enumerate(realm_ids):
        print(f"\n[{i+1}/{total_realms}] Scanning Realm ID: {realm_id}...")
        
        try:
            auctions_url = f'https://{region}.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions'
            headers = {'Authorization': f'Bearer {access_token}', 'Battlenet-Namespace': namespace}
            auctions_response = requests.get(auctions_url, headers=headers)
            auctions_response.raise_for_status()
            
            auctions_data = auctions_response.json().get('auctions', [])
            print(f"Found {len(auctions_data)} auctions.")
            
            if not auctions_data:
                print("No auctions found for this realm, skipping.")
                continue

            # Prepare data for bulk insertion
            scan_time = datetime.now()
            auctions_to_insert = []
            for auction in auctions_data:
                auctions_to_insert.append((
                    auction['id'],
                    auction['item']['id'],
                    realm_id,
                    auction.get('buyout'), # .get() safely returns None if no buyout
                    auction['quantity'],
                    auction['time_left'],
                    scan_time
                ))

            # Bulk insert the data for this realm
            cursor.executemany(
                "INSERT INTO auctions (id, item_id, connected_realm_id, buyout_price, quantity, time_left, scan_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                auctions_to_insert
            )
            conn.commit()
            print(f"Successfully saved {len(auctions_to_insert)} auctions to the database.")

        except requests.exceptions.RequestException as err:
            print(f"Could not fetch data for realm {realm_id}. Error: {err}")
            # Optional: wait a moment before trying the next realm
            time.sleep(2)
        except sqlite3.Error as err:
            print(f"Database error for realm {realm_id}. Error: {err}")

    # 5. Close the database connection
    conn.close()
    print("\n---------------------------------")
    print("Scanner finished. All realms have been processed.")
    print("Your database 'wow_auctions.db' is now populated with fresh data.")

if __name__ == "__main__":
    main()