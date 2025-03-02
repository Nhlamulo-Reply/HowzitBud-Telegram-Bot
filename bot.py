import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import paypalrestsdk
import uuid

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = ""

# PayPal Configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "",
    "client_secret":""
})

# Product Categories & Items
db_categories = {
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60, "Product3": 70, "Product4": 80, "Product5": 90, "Product6": 100, "Product7": 110, "Product8": 120}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70, "Product3": 75, "Product4": 85, "Product5": 95, "Product6": 105, "Product7": 115, "Product8": 125}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80, "Product3": 85, "Product4": 95, "Product5": 105, "Product6": 115, "Product7": 125, "Product8": 135}},
}

# User Cart Storage
user_cart = {}
user_position = {}
user_orders = {}
user_affiliate_codes = {}

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🛍 Menu"), KeyboardButton("🛒 View Cart")],
            [KeyboardButton("💳 Pay Now"), KeyboardButton("Skip")],
            [KeyboardButton("ℹ About"), KeyboardButton("❓ Help"), KeyboardButton("📞 Support")]
        ], resize_keyboard=True
    )

def get_category_buttons():
    buttons = [
        [InlineKeyboardButton(cat["name"], callback_data=f"category_{cat_id}")]
        for cat_id, cat in db_categories.items()
    ]
    return InlineKeyboardMarkup(buttons)

def get_product_buttons(category_id, position=0):
    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())
    chunk_size = 6
    chunks = [products[i:i + chunk_size] for i in range(0, len(products), chunk_size)]
    current_chunk = position // chunk_size
    current_products = chunks[current_chunk]

    buttons = [
        [InlineKeyboardButton(f"{product} - R{price}", callback_data=f"product_{category_id}_{idx + (current_chunk * chunk_size)}")]
        for idx, (product, price) in enumerate(current_products)
    ]

    nav_buttons = []
    if current_chunk > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Back", callback_data=f"back_{category_id}_{(current_chunk - 1) * chunk_size}"))
    if current_chunk < len(chunks) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"next_{category_id}_{(current_chunk + 1) * chunk_size}"))

    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context):
    await update.message.reply_text("Welcome to our store!", reply_markup=get_main_menu())

async def show_menu(update: Update, context):
    await update.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def category_selected(update: Update, context):
    query = update.callback_query
    category_id = query.data.split("_")[1]
    user_position[query.from_user.id] = 0
    await query.message.edit_text(f"Products in {db_categories[category_id]['name']}",
                                  reply_markup=get_product_buttons(category_id))

async def product_navigation(update: Update, context):
    query = update.callback_query
    action, category_id, position = query.data.split("_")
    position = int(position)
    user_position[query.from_user.id] = position
    await query.message.edit_reply_markup(reply_markup=get_product_buttons(category_id, position))

async def product_selected(update: Update, context):
    query = update.callback_query
    _, category_id, position = query.data.split("_")
    position = int(position)
    product_name, price = list(db_categories[category_id]["products"].items())[position]

    user_id = query.from_user.id
    if user_id not in user_cart:
        user_cart[user_id] = []
    user_cart[user_id].append({"name": product_name, "price": price})

    await query.answer(f"{product_name} added to cart!")
    await query.message.edit_reply_markup(reply_markup=get_product_buttons(category_id, position))

async def view_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty.")
        return
    cart_details = "\n".join([f"{idx + 1}. {item['name']} - R{item['price']}" for idx, item in enumerate(cart_items)])
    await update.message.reply_text(f"Your Cart:\n{cart_details}\n\nReply with the item number to remove it.",
                                    reply_markup=get_main_menu())

async def remove_from_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    try:
        item_index = int(update.message.text.strip()) - 1
        if 0 <= item_index < len(cart_items):
            removed_item = cart_items.pop(item_index)
            await update.message.reply_text(f"Removed {removed_item['name']} from cart.")
        else:
            await update.message.reply_text("Invalid item number.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
    await view_cart(update, context)

async def skip_discount(update: Update, context):
    await pay_now(update, context)

async def pay_now(update: Update, context):
    await update.message.reply_text("Proceeding to payment. Select a method:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay with PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("₿ Pay with Bitcoin", callback_data="pay_bitcoin")],
        [InlineKeyboardButton("💳 Pay with FNB Card", callback_data="pay_fnb")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]))

async def handle_payment(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] for item in cart_items)

    if query.data == "pay_paypal":
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://example.com/return",
                "cancel_url": "https://example.com/cancel"
            },
            "transactions": [{
                "amount": {"total": f"{total_amount}", "currency": "USD"},
                "description": "Purchase from Telegram Bot"
            }]
        })
        if payment.create():
            for link in payment.links:
                if link.method == "REDIRECT":
                    redirect_url = link.href
                    await query.message.reply_text(f"Please proceed with your payment: {redirect_url}")
                    break
        else:
            logger.error(f"PayPal Payment Creation Failed: {payment.error}")
            await query.message.reply_text("Payment creation failed. Please try again.")
    elif query.data == "pay_bitcoin":
        bitcoin_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Replace with your Bitcoin address
        await query.message.reply_text(f"Please send R{total_amount} to the following Bitcoin address: {bitcoin_address}")
    elif query.data == "pay_fnb":
        await query.message.reply_text("Please use the following FNB account details for payment:\n\n"
                                       "Bank: FNB\n"
                                       "Account Number: 1234567890\n"
                                       "Branch Code: 250655\n"
                                       "Reference: Your Order Number")
    elif query.data == "back_to_menu":
        await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())

    # Generate and display order number
    order_number = str(uuid.uuid4())[:8]
    user_orders[user_id] = order_number
    await query.message.reply_text(f"Your order number is: {order_number}")

async def about(update: Update, context):
    await update.message.reply_text("This is a sample Telegram bot for an online store.")

async def help(update: Update, context):
    await update.message.reply_text("Help information: ...")

async def support(update: Update, context):
    await update.message.reply_text("Contact support at support@example.com.")

async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())

async def back_to_categories(update: Update, context):
    query = update.callback_query
    await query.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def handle_affiliate_code(update: Update, context):
    user_id = update.message.from_user.id
    affiliate_code = update.message.text.strip()
    user_affiliate_codes[user_id] = affiliate_code
    await update.message.reply_text(f"Affiliate code '{affiliate_code}' applied successfully!")

# Add Handlers
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Skip"), skip_discount))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), remove_from_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^AFF\d+$"), handle_affiliate_code))  # Affiliate code handler
application.add_handler(CallbackQueryHandler(category_selected, pattern="category_.*"))
application.add_handler(CallbackQueryHandler(product_selected, pattern="product_.*"))
application.add_handler(CallbackQueryHandler(product_navigation, pattern="(next|back)_.*"))
application.add_handler(CallbackQueryHandler(handle_payment, pattern="pay_.*"))
application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
application.add_handler(CallbackQueryHandler(back_to_categories, pattern="back_to_categories"))

if __name__ == "__main__":
    application.run_polling()