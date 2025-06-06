from dotenv import load_dotenv
import os
import requests

load_dotenv()

# --- Configuration ---
client_id = 'a446f3e402fb474eaeeab49a4ace4fe4'
client_secret = os.getenv("SECRET_KEY") # Replace with the secret you received
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

    # Print the name and ID of each connected realm
    for realm in connected_realms:
        # The actual ID is inside the 'href' URL, but the API also provides a direct ID field.
        realm_id = realm.get('id')
        # We need to get the realm name, which we can parse or get from another field
        # For this index, the name is not directly available, so we parse it from the 'href' as a simple example
        # A more robust way would be to call each href, but for a list, this is fine.
        # Let's check if there is a name field first
        # UPDATE: The Blizzard API reference confirms the 'id' is present. Let's assume a 'name' field is not, and parse it.
        # Let's just print the ID for now as it's what we primarily need.
        print(f"Connected Realm ID: {realm_id}")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error fetching realms: {err}")
    print(f"Response Body: {realms_response.text}")
except requests.exceptions.RequestException as err:
    print(f"Request Error fetching realms: {err}")