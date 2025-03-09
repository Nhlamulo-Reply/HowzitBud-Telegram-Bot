import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
import paypalrestsdk
import uuid
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = "7727498536:AAECs76djeGzWB8QbwA-gKWvEIVlcy2nAsg"

# Admin User ID (replace with your Telegram user ID)
ADMIN_USER_ID = 6963023458  # Replace with your actual Telegram user ID

# PayPal Configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "AQnqnmgRYjSp3ntW6ftVb72_DAW3W8IFM_u5ffg4RSJQa47DyXTWAqyt5m0BhUEx_vIfOi2iW003RMzS",
    "client_secret": "EDfxrULGQtOqRATgfPY9nezN4hPCwASvMFg7MwvsuzIdjRbyN9lOSdhTgMF4Hn6JkyeMSZzcYiiQ5Yrz"
})

# Product Categories & Items
db_categories = {
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80}},
}

# User Cart Storage
user_cart = {}
user_orders = {}
user_affiliate_codes = {}

# Affiliate Codes Storage
affiliate_codes = {"DISCOUNT10": {"expiry": datetime.now() + timedelta(days=30), "discount": 0.1}}

# Delivery Fee
DELIVERY_FEE = 100

# Conversation states
AFFILIATE_CODE, PAYMENT_METHOD = range(2)

def get_main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛍 Menu"), KeyboardButton("🛒 View Cart")],
        [KeyboardButton("💳 Pay Now"), KeyboardButton("Skip")],
        [KeyboardButton("ℹ About"), KeyboardButton("❓ Help"), KeyboardButton("📞 Support")]
    ], resize_keyboard=True)

async def start(update: Update, context):
    keyboard = [[KeyboardButton("▶ Start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to our store! Click 'Start' to continue.", reply_markup=get_main_menu())

async def show_menu(update: Update, context):
    buttons = [[InlineKeyboardButton(cat["name"], callback_data=f"category_{cat_id}")]
               for cat_id, cat in db_categories.items()]
    await update.message.reply_text("Select a category:", reply_markup=InlineKeyboardMarkup(buttons))

async def category_selected(update: Update, context):
    query = update.callback_query
    category_id = query.data.split("_")[1]
    products = db_categories[category_id]["products"]
    buttons = [[InlineKeyboardButton(f"{name} - R{price}", callback_data=f"product_{category_id}_{name}")]
               for name, price in products.items()]
    buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
    await query.message.edit_text(f"Products in {db_categories[category_id]['name']}", reply_markup=InlineKeyboardMarkup(buttons))

async def product_selected(update: Update, context):
    query = update.callback_query
    _, category_id, product_name = query.data.split("_")
    price = db_categories[category_id]["products"][product_name]
    user_id = query.from_user.id
    if user_id not in user_cart:
        user_cart[user_id] = []
    user_cart[user_id].append({"name": product_name, "price": price})
    await query.answer(f"{product_name} added to cart!")
    await query.message.delete()
    await query.message.reply_text("Item added! Choose another or go back to the menu.", reply_markup=get_main_menu())

async def view_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty.")
        return
    cart_details = "\n".join([f"{idx + 1}. {item['name']} - R{item['price']}" for idx, item in enumerate(cart_items)])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE
    await update.message.reply_text(f"Your Cart:\n{cart_details}\nTotal: R{total_amount}", reply_markup=get_main_menu())

async def pay_now(update: Update, context):
    user_id = update.message.from_user.id
    context.user_data["user_id"] = user_id
    await update.message.reply_text("Do you have an affiliate code? (Type 'yes' to enter or 'no' to skip):")
    return AFFILIATE_CODE

async def handle_affiliate_code(update: Update, context):
    user_response = update.message.text.strip().lower()
    if user_response == "yes":
        await update.message.reply_text("Enter your affiliate code:")
        return "AFFILIATE_CODE_INPUT"
    elif user_response == "no":
        await show_payment_methods(update, context)
        return PAYMENT_METHOD
    else:
        await update.message.reply_text("Invalid input. Type 'yes' or 'no'.")
        return AFFILIATE_CODE

async def apply_affiliate_code(update: Update, context):
    user_id = context.user_data["user_id"]
    code = update.message.text.strip()
    if code in affiliate_codes and datetime.now() < affiliate_codes[code]["expiry"]:
        user_affiliate_codes[user_id] = code
        await update.message.reply_text("Discount applied!")
        await show_payment_methods(update, context)
        return PAYMENT_METHOD
    else:
        await update.message.reply_text("Invalid or expired code.")
        return AFFILIATE_CODE

async def show_payment_methods(update: Update, context):
    buttons = [
        [InlineKeyboardButton("💳 Pay with PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("₿ Pay with Bitcoin", callback_data="pay_bitcoin")]
    ]
    await update.message.reply_text("Select a payment method:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_payment(update: Update, context):
    query = update.callback_query
    user_id = context.user_data["user_id"]
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE
    if user_id in user_affiliate_codes:
        total_amount *= 0.9
    if query.data == "pay_paypal":
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{"amount": {"total": f"{total_amount:.2f}", "currency": "USD"}}]
        })
        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    await query.message.reply_text(f"Complete payment: {link.href}")
                    return
        await query.message.reply_text("Payment creation failed.")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛍 Menu$"), show_menu))
app.add_handler(CallbackQueryHandler(category_selected, pattern="^category_"))
app.add_handler(CallbackQueryHandler(product_selected, pattern="^product_"))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💳 Pay Now$"), pay_now))
app.run_polling()
