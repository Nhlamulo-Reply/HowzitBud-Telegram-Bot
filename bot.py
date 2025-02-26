import logging
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import hashlib
import requests

# Bot Token and Payment Info
TOKEN = "YOUR_BOT_TOKEN"
PAYFAST_MERCHANT_ID = "YOUR_MERCHANT_ID"
PAYFAST_MERCHANT_KEY = "YOUR_MERCHANT_KEY"
PAYFAST_URL = "https://www.payfast.co.za/eng/process"
RETURN_URL = "https://yourwebsite.com/success"
CANCEL_URL = "https://yourwebsite.com/cancel"
NOTIFY_URL = "https://yourwebsite.com/notify"

# Sample Products and User Cart
db_products = {
    "1": {"name": "Product A", "price": 100.0},
    "2": {"name": "Product B", "price": 200.0},
}
user_cart = {}
users_logged_in = {}

# Initialize the bot application
application = Application.builder().token(TOKEN).build()

# Main Menu Keyboard
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Menu"), KeyboardButton(text="🛒 View Cart")],
        [KeyboardButton(text="📦 Orders"), KeyboardButton(text="💳 Pay Now")],
        [KeyboardButton(text="ℹ About"), KeyboardButton(text="❓ Help"), KeyboardButton(text="📞 Support")]
    ],
    resize_keyboard=True
)

# Payment Methods Keyboard
payment_methods_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💳 Pay with PayFast")],
        [KeyboardButton(text="🔙 Back to Menu")]
    ],
    resize_keyboard=True
)


# Command Handlers

async def start(update, context):
    user_id = update.message.from_user.id
    if user_id not in users_logged_in:
        # First-time user login
        await update.message.reply_text("Welcome! Please enter your username to get started.")
    else:
        await update.message.reply_text(f"Hello, {users_logged_in[user_id]}! How can I assist you today?",
                                        reply_markup=main_menu)


async def handle_username(update, context):
    user_id = update.message.from_user.id
    username = update.message.text.strip()
    users_logged_in[user_id] = username  # Store username in session
    await update.message.reply_text(f"Hello, {username}! You are now logged in. Choose an option:",
                                    reply_markup=main_menu)


async def show_menu(update, context):
    product_list = "\n".join([f"{key}: {item['name']} - R{item['price']}" for key, item in db_products.items()])
    await update.message.reply_text(
        f"Available Products:\n{product_list}\n\nReply with the product number to add to the cart.")


async def add_to_cart(update, context):
    user_id = update.message.from_user.id
    product_id = update.message.text.strip()
    if product_id in db_products:
        user_cart[user_id] = user_cart.get(user_id, []) + [db_products[product_id]]
        await update.message.reply_text(f"Successfully added {db_products[product_id]['name']} to your cart!")
    else:
        await update.message.reply_text("Invalid product ID. Please try again.")
    await update.message.reply_text("Choose an action:", reply_markup=main_menu)


async def remove_from_cart(update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Nothing to remove.")
        return

    # Display current cart and ask user to select which item to remove
    cart_details = "\n".join(
        [f"{index + 1}: {item['name']} - R{item['price']}" for index, item in enumerate(cart_items)])
    await update.message.reply_text(
        f"Your Cart:\n{cart_details}\n\nReply with the number of the product to remove from cart.")

    # Save the user’s next step to remove item
    context.user_data['removal_stage'] = True


async def handle_removal(update, context):
    if 'removal_stage' not in context.user_data or not context.user_data['removal_stage']:
        return

    user_id = update.message.from_user.id
    product_id = int(update.message.text.strip()) - 1  # Subtracting 1 to match cart index
    cart_items = user_cart.get(user_id, [])

    if product_id >= len(cart_items) or product_id < 0:
        await update.message.reply_text("Invalid selection. Please select a valid product number to remove.")
    else:
        removed_product = cart_items.pop(product_id)
        user_cart[user_id] = cart_items  # Update cart
        await update.message.reply_text(f"Successfully removed {removed_product['name']} from your cart.")

    await update.message.reply_text("Choose an action:", reply_markup=main_menu)
    context.user_data['removal_stage'] = False  # End the removal stage


async def view_cart(update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty.")
        return

    cart_details = "\n".join([f"{item['name']} - R{item['price']}" for item in cart_items])
    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(
        f"Your Cart:\n{cart_details}\n\nTotal: R{total_price}\n\nTo remove an item, type its number.\nTo proceed to checkout, type 'Checkout'.")


async def proceed_checkout(update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Please add items before proceeding.")
        return

    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(f"Proceeding to checkout. Total price: R{total_price}. Choose a payment method:",
                                    reply_markup=payment_methods_menu)


async def pay_now(update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text(
            "Your cart is empty. Please add items to the cart before proceeding to payment.")
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
    await update.message.reply_text(f"Click here to complete your payment:\n{payment_link}")


async def about(update, context):
    await update.message.reply_text(
        "This is an e-commerce bot. You can browse products, add them to the cart, and proceed to checkout!")


async def help_command(update, context):
    await update.message.reply_text(
        "Use the menu options to navigate through the bot, place orders, and make payments.")


async def support(update, context):
    await update.message.reply_text("Contact support at support@example.com for any assistance.")


# Add Handlers to Dispatcher
application.add_handler(CommandHandler("start", start))
application.add_handler(
    MessageHandler(filters.TEXT & filters.Regex(r"^\S+$"), handle_username))  # Handles username input for login
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(
    MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), add_to_cart))  # Only digits for product ID
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📦 Orders"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help_command))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Checkout"), proceed_checkout))  # Checkout handler
application.add_handler(
    MessageHandler(filters.TEXT & filters.Regex("🔙 Back to Menu"), show_menu))  # Back to menu handler
application.add_handler(
    MessageHandler(filters.TEXT & filters.Regex("🛒 Remove"), remove_from_cart))  # Remove item from cart
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), handle_removal))  # Handle item removal

# Start the bot
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    application.run_polling()
