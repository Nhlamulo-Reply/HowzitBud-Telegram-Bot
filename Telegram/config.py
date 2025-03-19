# Bot Token
TOKEN = "7727498536:AAECs76djeGzWB8QbwA-gKWvEIVlcy2nAsg"

# Admin User ID (replace with your Telegram user ID)
ADMIN_USER_ID = 6963023458  # Replace with your actual Telegram user ID
affiliate_codes, user_orders, user_cart = {}

# PayPal Configuration
PAYPAL_CONFIG = {
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "AQnqnmgRYjSp3ntW6ftVb72_DAW3W8IFM_u5ffg4RSJQa47DyXTWAqyt5m0BhUEx_vIfOi2iW003RMzS",
    "client_secret": "EDfxrULGQtOqRATgfPY9nezN4hPCwASvMFg7MwvsuzIdjRbyN9lOSdhTgMF4Hn6JkyeMSZzcYiiQ5Yrz"
}

# Product Categories & Items
db_categories = {
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60, "Product3": 70, "Product4": 80, "Product5": 90, "Product6": 100, "Product7": 110, "Product8": 120}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70, "Product3": 75, "Product4": 85, "Product5": 95, "Product6": 105, "Product7": 115, "Product8": 125}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80, "Product3": 85, "Product4": 95, "Product5": 105, "Product6": 115, "Product7": 125, "Product8": 135}},
}

# Delivery Fee
DELIVERY_FEE = 100  # Default delivery fee of R100