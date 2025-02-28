import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import paypalrestsdk
import hashlib

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# PayPal Configuration
# Bot Token and Payment Info
TOKEN = "7481918040:AAHxJjyaLFRgKV_5pLAEx6KItrazmTSwtpM"
PAYPAL_MERCHANT_ID = "AQnqnmgRYjSp3ntW6ftVb72_DAW3W8IFM_u5ffg4RSJQa47DyXTWAqyt5m0BhUEx_vIfOi2iW003RMzS"
PAYPAL_MERCHANT_KEY = "EDfxrULGQtOqRATgfPY9nezN4hPCwASvMFg7MwvsuzIdjRbyN9lOSdhTgMF4Hn6JkyeMSZzcYiiQ5Yrz"
PAYFAST_MERCHANT_ID = "YOUR_PAYFAST_MERCHANT_ID"
PAYFAST_MERCHANT_KEY = "YOUR_PAYFAST_MERCHANT_KEY"
PAYFAST_URL = "https://www.payfast.co.za/eng/process"
RETURN_URL = "https://yourwebsite.com/success"  # Replace with your actual URL
CANCEL_URL = "https://yourwebsite.com/cancel"  # Replace with your actual URL
NOTIFY_URL = "https://yourwebsite.com/notify"  # Replace with your actual URL

paypalrestsdk.configure({
    "mode": "sandbox",  # Set to "live" for productionn
    "client_id": "AQnqnmgRYjSp3ntW6ftVb72_DAW3W8IFM_u5ffg4RSJQa47DyXTWAqyt5m0BhUEx_vIfOi2iW003RMzS",
    "client_secret": "EDfxrULGQtOqRATgfPY9nezN4hPCwASvMFg7MwvsuzIdjRbyN9lOSdhTgMF4Hn6JkyeMSZzcYiiQ5Yrz"
})

# Sample Products and User Cart
db_products = {
    "1": {"name": "Product A", "price": 100.0},
    "2": {"name": "Product B", "price": 200.0},
}

user_cart = {}

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
        [InlineKeyboardButton(text="💳 Pay with BitCoin")],
        [InlineKeyboardButton(text="💳 Pay with PayPal")],
        [InlineKeyboardButton(text="🔙 Back to Menu")]
    ],
    resize_keyboard=True
)

# Create PayPal Payment Link
def create_payment_link(amount):
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": RETURN_URL,
            "cancel_url": CANCEL_URL
        },
        "transactions": [{
            "amount": {
                "total": str(amount),
                "currency": "USD"
            },
            "description": "Payment for goods"
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return link.href
    else:
        return None

# Start Command Handler
async def start(update: Update, context):
    await update.message.reply_text("Hello! Welcome to the Payment Bot. Type /pay to start payment.", reply_markup=main_menu)

# Show Menu (Display products to choose from)
async def show_menu(update: Update, context):
    product_list = "\n".join([f"{key}: {item['name']} - R{item['price']}" for key, item in db_products.items()])
    await update.message.reply_text(
        f"Available Products:\n{product_list}\n\nReply with the product number to add to the cart.",
        reply_markup=main_menu)

# Add Product to Cart
async def add_to_cart(update: Update, context):
    user_id = update.message.from_user.id
    product_id = update.message.text.strip()

    if product_id in db_products:
        if user_id not in user_cart:
            user_cart[user_id] = []
        product = db_products[product_id]
        user_cart[user_id].append(product)
        await update.message.reply_text(f"Successfully added {product['name']} to your cart!")
        await update.message.reply_text("Choose an action:", reply_markup=main_menu)
    else:
        await update.message.reply_text("Invalid product ID. Please try again.")

# View Cart
async def view_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty.")
        return
    cart_details = "\n".join([f"{item['name']} - R{item['price']}" for item in cart_items])
    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(
        f"Your Cart:\n{cart_details}\n\nTotal: R{total_price}\n\nTo proceed to checkout, type 'Checkout'.",
        reply_markup=main_menu)

# Pay Now Command Handler
async def pay_now(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Please add items before proceeding.")
        return
    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(
        f"Proceeding to checkout. Total: R{total_price}. Choose a payment method:",
        reply_markup=payment_methods_menu)

# Proceed to Checkout
async def proceed_checkout(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Please add items before proceeding.")
        return
    total_price = sum(item['price'] for item in cart_items)
    await update.message.reply_text(
        f"Proceeding to checkout. Total: R{total_price}. Choose a payment method:",
        reply_markup=payment_methods_menu)

# Pay with PayFast
async def pay_with_payfast(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Please add items to the cart before proceeding.")
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


# Pay with PayPal
async def pay_with_paypal(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty. Please add items to the cart before proceeding.")
        return
    total_price = sum(item['price'] for item in cart_items)

    # Create the PayPal payment link
    payment_link = create_payment_link(amount=total_price)

    # Send the payment link to the user
    if payment_link:
        await update.message.reply_text(f"Click here to complete your PayPal payment:\n{payment_link}")
    else:
        await update.message.reply_text("Sorry, there was an error generating the payment link.")


# Back to Menu
async def back_to_menu(update: Update, context):
    await update.message.reply_text("Back to the main menu.", reply_markup=main_menu)

# About Section
async def about(update: Update, context):
    await update.message.reply_text("This is the about section of our e-commerce platform.", reply_markup=main_menu)

# Help Section
async def help(update: Update, context):
    await update.message.reply_text("Here is some help information for using the bot.", reply_markup=main_menu)

# Support Section
async def support(update: Update, context):
    await update.message.reply_text("For support, contact us at support@ourplatform.com.", reply_markup=main_menu)



# Add Handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), add_to_cart))  # Only digits for product ID
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now))  # Pay Now handler
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("💳 Pay with PayFast"), pay_with_payfast))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("💳 Pay with PayPal"), pay_with_paypal))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📦 Orders"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Checkout"), proceed_checkout))
# Add Handlers to the application
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🔙 Back to Menu"), back_to_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))


if __name__ == "__main__":
    application.run_polling()
