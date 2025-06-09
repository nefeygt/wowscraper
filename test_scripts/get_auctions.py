from dotenv import load_dotenv
import os
import requests

load_dotenv()

# --- Configuration ---
client_id = 'a446f3e402fb474eaeeab49a4ace4fe4'
client_secret = os.getenv("SECRET_KEY") # Replace with your secret
region = 'eu'
namespace = f'dynamic-{region}'
locale = 'en_US'

# --- The ID of the realm we want to scan ---
# We're using the first one from your list as an example.
target_realm_id = 1080 

# --- Step 1: Get Access Token ---
# (This part is the same as before)
token_url = f'https://{region}.oauth.battle.net/token'
token_payload = {'grant_type': 'client_credentials'}

try:
    token_response = requests.post(token_url, data=token_payload, auth=(client_id, client_secret))
    token_response.raise_for_status()
    access_token = token_response.json()['access_token']
    print("Successfully obtained access token!")
except Exception as err:
    print(f"Error obtaining token: {err}")
    exit()

# --- Step 2: Fetch Auction Data for the Target Realm ---
auctions_url = f'https://{region}.api.blizzard.com/data/wow/connected-realm/{target_realm_id}/auctions'

api_headers = {
    'Authorization': f'Bearer {access_token}',
    'Battlenet-Namespace': namespace
}

api_params = {
    'locale': locale
}

try:
    print(f"\nFetching auction data for Connected Realm ID: {target_realm_id}...")
    auctions_response = requests.get(auctions_url, headers=api_headers, params=api_params)
    auctions_response.raise_for_status()
    
    data = auctions_response.json()
    auctions = data.get('auctions', [])
    
    if auctions:
        print(f"Success! Found {len(auctions)} active auctions.")
        print("-" * 30)
        print("Here is a sample of the first 5 auctions:")

        for auction in auctions[:5]:
            item_id = auction['item']['id']
            quantity = auction.get('quantity')
            buyout_price = auction.get('buyout')
            time_left = auction.get('time_left')
            
            # Buyout price is in copper. Let's format it for readability.
            if buyout_price:
                gold = int(buyout_price / 10000)
                silver = int((buyout_price % 10000) / 100)
                copper = int(buyout_price % 100)
                formatted_price = f"{gold}g {silver}s {copper}c"
            else:
                formatted_price = "No buyout (Bid only)"

            print(f"-> Item ID: {item_id}, Quantity: {quantity}, Buyout: {formatted_price}, Time Left: {time_left}")
    else:
        print("The response did not contain any auctions.")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error fetching auctions: {err}")
    print(f"Response Body: {auctions_response.text}")
except Exception as err:
    print(f"An error occurred: {err}")