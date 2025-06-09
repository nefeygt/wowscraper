from dotenv import load_dotenv
import os
import requests

load_dotenv()

# --- Replace these with your actual Client ID and Client Secret ---
client_id = 'a446f3e402fb474eaeeab49a4ace4fe4'
client_secret = os.getenv("SECRET_KEY") # Replace with the secret you received
# ----------------------------------------------------------------

# The Blizzard API endpoint for generating an access token
token_url = 'https://oauth.battle.net/token'

# The data to send in the request to get the token
payload = {
    'grant_type': 'client_credentials'
}

# Make the POST request with your client_id and client_secret for authentication
try:
    response = requests.post(token_url, data=payload, auth=(client_id, client_secret))

    # Raise an exception if the request was not successful (e.g., 401 Unauthorized)
    response.raise_for_status() 

    # If the request was successful, the token is in the JSON response
    token_data = response.json()
    access_token = token_data['access_token']
    
    print("Successfully obtained access token!")
    print(f"Access Token: {access_token}")
    print(f"Expires in: {token_data['expires_in']} seconds (24 hours)")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error: {err}")
    print("Failed to get access token. Check your Client ID and Client Secret.")
except requests.exceptions.RequestException as err:
    print(f"Request Error: {err}")