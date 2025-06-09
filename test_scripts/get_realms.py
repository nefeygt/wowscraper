from dotenv import load_dotenv
import os
import requests

load_dotenv()

# --- Configuration ---
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("SECRET_KEY")
region = 'eu'
namespace = f'dynamic-{region}'
locale = 'en_US'

# --- Step 1: Get Access Token ---

token_url = f'https://{region}.oauth.battle.net/token'
token_payload = {'grant_type': 'client_credentials'}

try:
    token_response = requests.post(token_url, data=token_payload, auth=(client_id, client_secret))
    token_response.raise_for_status()
    access_token = token_response.json()['access_token']
    print("Successfully obtained access token!\n")
except requests.exceptions.HTTPError as err:
    print(f"HTTP Error obtaining token: {err}")
    exit() # Exit the script if we can't get a token
except requests.exceptions.RequestException as err:
    print(f"Request Error obtaining token: {err}")
    exit()

# --- Step 2: Use Access Token to Fetch Connected Realms ---

# The API endpoint for the connected realm index
realms_url = f'https://{region}.api.blizzard.com/data/wow/connected-realm/index'

# The headers required for an authenticated API call
api_headers = {
    'Authorization': f'Bearer {access_token}',
    'Battlenet-Namespace': namespace
}

# The query parameters for the request
api_params = {
    'locale': locale
}

try:
    print("Fetching connected realms for EU region...")
    realms_response = requests.get(realms_url, headers=api_headers, params=api_params)
    realms_response.raise_for_status()
    
    # Parse the JSON response
    realms_data = realms_response.json()
    connected_realms = realms_data.get('connected_realms', [])
    
    print(f"\nFound {len(connected_realms)} connected realms.")
    print("-" * 30)

    import re

    for realm in connected_realms:
        href = realm.get('href')
        # Extract the ID using regex
        match = re.search(r'/connected-realm/(\d+)', href)
        if match:
            realm_id = match.group(1)
            print(f"Connected Realm ID: {realm_id}")
        else:
            print("Could not extract ID from href:", href)

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error fetching realms: {err}")
    print(f"Response Body: {realms_response.text}")
except requests.exceptions.RequestException as err:
    print(f"Request Error fetching realms: {err}")