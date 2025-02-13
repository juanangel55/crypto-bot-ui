import json
import sqlite3
import requests
import time
from bs4 import BeautifulSoup
from telegram import Bot

# Load config file
with open("config.json", "r") as f:
    config = json.load(f)

# Extract settings
FILTERS = config["filters"]
COIN_BLACKLIST = set(config["blacklist"]["coins"])
DEV_BLACKLIST = set(config["blacklist"]["devs"])
FAKE_VOLUME_SETTINGS = config["fake_volume_detection"]
RUGCHECK_SETTINGS = config["rugcheck"]
BUNDLED_SUPPLY_SETTINGS = config["bundled_supply"]

# API URLs and keys
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens/"
RUGCHECK_API_URL = "https://api.rugcheck.xyz/v1/check"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = "your_etherscan_api_key"
BONKBOT_API_URL = "https://api.bonkbot.com/v1/trade"
BONKBOT_API_KEY = "your_bonkbot_api_key"
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_telegram_chat_id"

# Initialize Telegram bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

def fetch_token_data(token_address):
    """Fetch token data from DexScreener."""
    response = requests.get(f"{DEXSCREENER_API_URL}{token_address}")
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, dict) and 'pairs' in data:
            return data
        else:
            print(f"Invalid data structure for token: {token_address}")
    else:
        print(f"Failed to fetch data for token: {token_address}")
    return None

def is_blacklisted(token_data):
    """Check if a token or its developer is blacklisted."""
    if not token_data or not isinstance(token_data, dict):
        print("Invalid token data provided.")
        return False

    pairs = token_data.get('pairs', [])
    if not pairs or not isinstance(pairs, list):
        print("No pairs data found.")
        return False

    token = pairs[0] if pairs else {}
    if not token or not isinstance(token, dict):
        print("Invalid token data in pairs.")
        return False

    token_address = token.get('baseToken', {}).get('address')
    dev_address = token.get('baseToken', {}).get('deployer')

    if token_address in COIN_BLACKLIST:
        print(f"Token {token_address} is blacklisted.")
        return True
    if dev_address in DEV_BLACKLIST:
        print(f"Token {token_address} is created by blacklisted dev {dev_address}.")
        return True

    return False

def passes_filters(token_data):
    """Check if a token passes the defined filters."""
    token = token_data.get('pairs', [{}])[0]
    liquidity = token.get('liquidity', {}).get('usd', 0)
    volume_24h = token.get('volume', {}).get('h24', 0)
    market_cap = token.get('fdv', 0)

    if liquidity < FILTERS["min_liquidity"]:
        print(f"Token {token['baseToken']['address']} fails liquidity filter.")
        return False
    if volume_24h < FILTERS["min_volume_24h"]:
        print(f"Token {token['baseToken']['address']} fails 24h volume filter.")
        return False
    if market_cap > FILTERS["max_market_cap"]:
        print(f"Token {token['baseToken']['address']} fails market cap filter.")
        return False
    return True

def is_fake_volume(token_data):
    """Detect fake volume using an algorithmic approach."""
    token = token_data.get('pairs', [{}])[0]
    liquidity = token.get('liquidity', {}).get('usd', 0)
    volume_24h = token.get('volume', {}).get('h24', 0)
    price_change = token.get('priceChange', {}).get('h24', 0)

    if liquidity > 0 and volume_24h / liquidity > FAKE_VOLUME_SETTINGS["volume_liquidity_ratio_threshold"]:
        print(f"Token {token['baseToken']['address']} has suspicious volume/liquidity ratio.")
        return True
    if volume_24h > 100000 and abs(price_change) < FAKE_VOLUME_SETTINGS["price_stability_threshold"]:
        print(f"Token {token['baseToken']['address']} has high volume but stable price.")
        return True
    return False

def fetch_rugcheck_data(token_address):
    """Fetch contract rating from RugCheck.xyz."""
    response = requests.get(f"{RUGCHECK_API_URL}?address={token_address}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch RugCheck data for token: {token_address}")
        return None

def is_supply_bundled(token_address):
    """Check if the token's supply is bundled."""
    params = {
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": token_address,
        "address": "0xLargestHolderAddress",  # Replace with logic to fetch largest holder
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        largest_holder_balance = int(data.get("result", 0))
        total_supply = fetch_total_supply(token_address)
        if total_supply > 0 and largest_holder_balance / total_supply > BUNDLED_SUPPLY_SETTINGS["threshold"]:
            return True
    return False

def fetch_total_supply(token_address):
    """Fetch the total supply of a token."""
    params = {
        "module": "stats",
        "action": "tokensupply",
        "contractaddress": token_address,
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return int(data.get("result", 0))
    return 0

def update_blacklists(token_data):
    """Update blacklists based on RugCheck rating and bundled supply."""
    token = token_data.get('pairs', [{}])[0]
    token_address = token.get('baseToken', {}).get('address')
    dev_address = token.get('baseToken', {}).get('deployer')

    rugcheck_data = fetch_rugcheck_data(token_address)
    if rugcheck_data and rugcheck_data.get("rating") != RUGCHECK_SETTINGS["min_rating"]:
        print(f"Token {token_address} is marked as {rugcheck_data.get('rating')} on RugCheck.")
        COIN_BLACKLIST.add(token_address)
        DEV_BLACKLIST.add(dev_address)

    if is_supply_bundled(token_address):
        print(f"Token {token_address} has a bundled supply.")
        COIN_BLACKLIST.add(token_address)
        DEV_BLACKLIST.add(dev_address)

def execute_trade(action, token_address, amount):
    """Execute a trade using BonkBot."""
    payload = {
        "action": action,  # "buy" or "sell"
        "token_address": token_address,
        "amount": amount,
        "api_key": BONKBOT_API_KEY
    }
    response = requests.post(BONKBOT_API_URL, json=payload)
    if response.status_code == 200:
        print(f"Trade executed: {action} {amount} of {token_address}")
        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Trade executed: {action} {amount} of {token_address}")
        return True
    else:
        print(f"Failed to execute trade: {response.text}")
        return False

def save_token_data(token_data):
    """Save token data to the database if it passes all checks."""
    if not token_data or not isinstance(token_data, dict):
        print("Invalid token data provided.")
        return

    if is_blacklisted(token_data):
        return
    if not passes_filters(token_data):
        return
    if is_fake_volume(token_data):
        return

    conn = sqlite3.connect("dex_data.db")
    cursor = conn.cursor()
    token = token_data.get('pairs', [{}])[0]
    cursor.execute('''
        INSERT OR REPLACE INTO tokens (
            token_address, name, price_usd, liquidity, volume_24h, market_cap, dev_address
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        token.get('baseToken', {}).get('address'),
        token.get('baseToken', {}).get('name'),
        token.get('priceUsd'),
        token.get('liquidity', {}).get('usd'),
        token.get('volume', {}).get('h24'),
        token.get('fdv'),
        token.get('baseToken', {}).get('deployer')
    ))
    conn.commit()
    conn.close()
    print(f"Saved data for token: {token['baseToken']['address']}")

def run_bot():
    """Run the bot periodically."""
    while True:
        token_addresses = ["0xToken1", "0xToken2"]  # Replace with actual token addresses
        for address in token_addresses:
            token_data = fetch_token_data(address)
            if token_data:
                save_token_data(token_data)
                if not is_blacklisted(token_data):
                    execute_trade("buy", address, 1)  # Replace with your trading logic

        time.sleep(3600)  # Wait for 1 hour before the next run

if __name__ == "__main__":
    run_bot()
