import logging
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import hashlib
import requests

TOKEN = "7481918040:AAHxJjyaLFRgKV_5pLAEx6KItrazmTSwtpM"
PAYFAST_MERCHANT_ID = "YOUR_MERCHANT_ID"
PAYFAST_MERCHANT_KEY = "YOUR_MERCHANT_KEY"
PAYFAST_URL = "https://www.payfast.co.za/eng/process"
RETURN_URL = "https://yourwebsite.com/success"
CANCEL_URL = "https://yourwebsite.com/cancel"
NOTIFY_URL = "https://yourwebsite.com/notify"

# Initialize the Bot and Application
application = Application.builder().token(TOKEN).build()

# Keyboard Buttons
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Menu"), KeyboardButton(text="🛒 View Cart")],
        [KeyboardButton(text="📦 Orders"), KeyboardButton(text="💳 Pay Now")],
        [KeyboardButton(text="ℹ About"), KeyboardButton(text="❓ Help"), KeyboardButton(text="📞 Support")]
    ],
    resize_keyboard=True
)

# Sample products and cart
db_products = {
    "1": {"name": "Product A", "price": 100.0},
    "2": {"name": "Product B", "price": 200.0},
}
user_cart = {}

# Command Handlers
async def start(update, context):
    user_name = update.message.from_user.first_name
    greeting_message = f"Hello {user_name}! Welcome to our store. Choose an option below to get started:"
    await update.message.reply_text(greeting_message, reply_markup=main_menu)

async def show_instructions(update, context):
    instructions = (
        "To get started, select a product from the menu by typing the product number.\n"
        "You can also view your cart, check out, or proceed with any other option.\n"
        "Once you select a product, it will be added to your cart!"
    )
    await update.message.reply_text(instructions, reply_markup=main_menu)

async def show_menu(update, context):
    product_list = "\n".join([f"{key}: {item['name']} - R{item['price']}" for key, item in db_products.items()])
    await update.message.reply_text(f"Available Products:\n{product_list}\n\nReply with product number to add to cart.", reply_markup=main_menu)

async def add_to_cart(update, context):
    product_id = update.message.text
    if product_id in db_products:
        user_cart[update.message.from_user.id] = user_cart.get(update.message.from_user.id, []) + [db_products[product_id]]
        await update.message.reply_text(f"Success! {db_products[product_id]['name']} has been added to your cart. You can add more products or proceed to checkout.", reply_markup=main_menu)
    else:
        await update.message.reply_text("Invalid product ID. Please try again.", reply_markup=main_menu)

async def view_cart(update, context):
    cart_items = user_cart.get(update.message.from_user.id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Add products to your cart before proceeding.", reply_markup=main_menu)
        return
    cart_details = "\n".join([f"{item['name']} - R{item['price']}" for item in cart_items])
    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(f"Your Cart:\n{cart_details}\n\nTotal: R{total_price}", reply_markup=main_menu)

async def pay_now(update, context):
    cart_items = user_cart.get(update.message.from_user.id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Add items before proceeding to payment.", reply_markup=main_menu)
        return
    total_price = sum(item['price'] for item in cart_items)
    payment_data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "amount": total_price,
        "item_name": "E-Commerce Order",
        "return_url": RETURN_URL,
        "cancel_url": CANCEL_URL,
        "notify_url": NOTIFY_URL
    }
    query_string = "&".join([f"{key}={value}" for key, value in payment_data.items()])
    secure_hash = hashlib.md5(query_string.encode()).hexdigest()
    payment_link = f"{PAYFAST_URL}?{query_string}&signature={secure_hash}"
    await update.message.reply_text(f"Click the link below to complete your payment:\n{payment_link}", reply_markup=main_menu)

async def about(update, context):
    await update.message.reply_text("This is an e-commerce bot. Buy products easily! Browse the menu to get started.", reply_markup=main_menu)

async def help_command(update, context):
    await update.message.reply_text("Use the menu to navigate and place orders. You can add items to your cart and proceed to checkout.", reply_markup=main_menu)

async def support(update, context):
    await update.message.reply_text("Contact us at support@example.com. We're here to help!", reply_markup=main_menu)

# Add Handlers to Dispatcher
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help_command))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), add_to_cart))  # Only digits (product selection)

# Start the Bot
def run_bot():
    logging.basicConfig(level=logging.INFO)
    application.run_polling()

if __name__ == "__main__":
    run_bot()
