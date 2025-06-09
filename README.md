# WoW Auction House Scraper & Deal Finder

This project scrapes World of Warcraft auction house data using the Blizzard API, stores it in a SQLite database, and provides a web interface to find potential deals based on price differences across realms.

## Features

*   Fetches auction data for all connected realms in a specified region.
*   Caches item details (name, quality, icon) to reduce API calls.
*   Caches realm names.
*   Identifies potential deals by comparing item prices across different realms.
*   Web interface (Flask app) to display identified deals with pagination.
*   Uses statistical methods (IQR) to filter out extreme price outliers for more realistic deal identification.

## Project Structure

*   `app.py`: Flask web application to display deals.
*   `scanner.py`: Core script to fetch auction data and item details from the Blizzard API and store them in the database.
*   `update_realms_cache.py`: Script to fetch and store connected realm names.
*   `setup_database.py`: Script to initialize the SQLite database and create necessary tables.
*   `find_deals.py`: Console-based script to analyze and find deals (alternative to the web app).
*   `query_prices.py`: Utility script to query prices for a specific item ID.
*   `templates/index.html`: HTML template for the web application.
*   `.env`: Configuration file for API keys (should be in `.gitignore`).
*   `wow_auctions.db`: SQLite database file (should be in `.gitignore`).

## Setup

1.  **Prerequisites:**
    *   Python 3.7+
    *   A Blizzard Developer account and API client credentials (ID and Secret).

2.  **Clone the repository:**
    ```bash
    git clone <https://github.com/nefeygt/wowscraper.git>
    cd wowscraper
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt 
    ```

5.  **Configure API Credentials:**
    *   Create a file named `.env` in the project root.
    *   Add your Blizzard API client secret to it:
        ```properties
        // filepath: .env
        SECRET_KEY=YOUR_BLIZZARD_API_CLIENT_SECRET
        CLIENT_ID=YOUR_BLIZZARD_API_CLIENT_ID # Not private, globally unique
        ```

## Running the Application

1.  **Initial Database Setup (Run once):**
    ```bash
    python setup_database.py
    ```

2.  **Populate Realm Names (Run once, or periodically to update):**
    ```bash
    python update_realms_cache.py
    ```

3.  **Scan Auction Data (Run daily or as needed):**
    ```bash
    python scanner.py
    ```
    This script can take a significant amount of time as it fetches data for all realms and items.

4.  **Run the Web Application:**
    ```bash
    flask run 
    ```
    (Or `python app.py` if you have `app.run(debug=True)` at the end)
    Open your browser and go to `http://127.0.0.1:5000`.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
