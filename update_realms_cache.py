from dotenv import load_dotenv
import os
import requests
import sqlite3

load_dotenv()

# --- Configuration ---
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("SECRET_KEY")
region = 'eu'
namespace = f'dynamic-{region}'
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

def main():
    print("Starting realm cache update...")
    access_token = get_access_token()
    if not access_token:
        return

    headers = {'Authorization': f'Bearer {access_token}', 'Battlenet-Namespace': namespace}
    
    # 1. Get the index of all connected realms
    index_url = f"https://{region}.api.blizzard.com/data/wow/connected-realm/index"
    response = requests.get(index_url, headers=headers)
    response.raise_for_status()
    connected_realms_index = response.json().get('connected_realms', [])
    
    print(f"Found {len(connected_realms_index)} connected realms. Fetching details...")

    realms_to_insert = []
    for realm_ref in connected_realms_index:
        try:
            # 2. For each connected realm, fetch its detailed information
            details_url = realm_ref['href']
            details_response = requests.get(details_url, headers=headers)
            details_response.raise_for_status()
            details = details_response.json()
            
            connected_realm_id = details['id']
            # Join the names of the realms in the connection, e.g., "Khadgar / Bloodhoof"
            realm_names = " / ".join(sorted([realm['name']['en_US'] for realm in details['realms']]))
            
            realms_to_insert.append((connected_realm_id, realm_names))
            print(f"Fetched: {realm_names} (ID: {connected_realm_id})")

        except requests.exceptions.RequestException as err:
            print(f"Could not fetch details for a realm. Error: {err}")

    # 3. Insert all fetched realm names into the database
    if realms_to_insert:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Use "INSERT OR REPLACE" to update existing entries if the script is run again
        cursor.executemany("INSERT OR REPLACE INTO realms (connected_realm_id, name) VALUES (?, ?)", realms_to_insert)
        conn.commit()
        conn.close()
        print(f"\nSuccessfully saved {len(realms_to_insert)} realm names to the database.")

if __name__ == "__main__":
    main()