import logging

from ccxt import BadRequest
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, CallbackContext
import paypalrestsdk
import uuid
import re

from datetime import datetime

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

# User Cart Storage
user_cart = {}
user_position = {}
user_orders = {}
user_AFFILIATE_codes = {}
first_time_users ={}


# AFFILIATE Codes Storage
AFFILIATE_codes = {}  # Format: {"code": {"expiry": datetime, "AFFILIATE": 0.1}}

# Delivery Fee
DELIVERY_FEE = 100  # Default delivery fee of R100
ENTER_QUANTITY = 1

# Conversation states
FULL_NAME, PHONE, ADDRESS, CITY, COUNTRY, CONFIRM, DISCOUNT_CODE, PAYMENT_CONFIRMATION, NEXT_STEP = range(9)
AFFILIATE_CODE, AFFILIATE_CODE_INPUT, PAYMENT_METHOD, ADD_PRODUCT, REMOVE_PRODUCT, GENERATE_CODE = range(6)

db_categories = {
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60, "Product3": 70, "Product4": 80, "Product5": 90, "Product6": 100, "Product7": 110, "Product8": 120}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70, "Product3": 75, "Product4": 85, "Product5": 95, "Product6": 105, "Product7": 115, "Product8": 125}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80, "Product3": 85, "Product4": 95, "Product5": 105, "Product6": 115, "Product7": 125, "Product8": 135}},
}

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🛍 Menu"), KeyboardButton("🛒 View Cart")],
            [KeyboardButton("💳 Pay Now"), KeyboardButton("Track Order")],
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

    buttons = []

    for idx, (product, price) in enumerate(current_products):
        product_idx = idx + (current_chunk * chunk_size)
        # Debugging: Print category_id and product_idx
        print(f"category_id: {category_id}, product_idx: {product_idx}")
        buttons.append([
            InlineKeyboardButton(f"🛒 Add {product} - R{price}", callback_data=f"add_{category_id}_{product_idx}"),
            InlineKeyboardButton("➕ Set Quantity", callback_data=f"set_quantity_{category_id}_{product_idx}")
        ])

    nav_buttons = []
    if current_chunk > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅ Back", callback_data=f"back_{category_id}_{(current_chunk - 1) * chunk_size}"))
    if current_chunk < len(chunks) - 1:
        nav_buttons.append(
            InlineKeyboardButton("Next ➡", callback_data=f"next_{category_id}_{(current_chunk + 1) * chunk_size}"))

    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(buttons)

async def set_quantity(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    try:
        _, _, category_id, product_idx = callback_data.split("_")
        product_idx = int(product_idx)
    except ValueError:
        await query.answer("❌ Invalid data format. Please try again.")
        return

    context.user_data["selected_product"] = (category_id, product_idx)
    context.user_data["awaiting_quantity"] = True  # Set flag
    # Get the product name for the selected product
    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, _ = products[product_idx]

        # Prompt user to enter quantity for the selected product
        await query.answer()
        await query.message.reply_text(f"📝 Enter the number of quantity/products you want for {product_name}:")

    return ENTER_QUANTITY  # Move to quantity input step

async def enter_quantity(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    quantity_text = update.message.text.strip()

    if not quantity_text.isdigit() or int(quantity_text) <= 0:
        await update.message.reply_text("❌ Invalid quantity. Please enter a positive number:")
        return ENTER_QUANTITY  # Stay in the same state

    quantity = int(quantity_text)
    category_id, product_idx = context.user_data.get("selected_product", (None, None))

    if category_id is None or product_idx is None:
        await update.message.reply_text("❌ Something went wrong. Please try again.")
        return ConversationHandler.END

    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, price = products[product_idx]

        # Store in cart
        if user_id not in user_cart:
            user_cart[user_id] = []

        user_cart[user_id].append({"name": product_name, "price": price, "quantity": quantity})
        await update.message.reply_text(f"✅ Added {quantity}x {product_name} to cart!")
    else:
        await update.message.reply_text("❌ Invalid product selection.")

    context.user_data["awaiting_quantity"] = False  # Reset flag
    return ConversationHandler.END  # End the conversation

    user_id = update.message.from_user.id
    quantity = update.message.text.strip()

    # Validate input
    if not quantity.isdigit() or int(quantity) <= 0:
        await update.message.reply_text("❌ Invalid quantity. Please enter a positive number:")
        return ENTER_QUANTITY  # Stay in the same state

    quantity = int(quantity)
    category_id, product_idx = context.user_data.get("selected_product", (None, None))

    if category_id is None or product_idx is None:
        await update.message.reply_text("❌ Something went wrong. Please try again.")
        return ConversationHandler.END

    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, price = products[product_idx]

        # Store in cart
        if user_id not in user_cart:
            user_cart[user_id] = []

        user_cart[user_id].append({"name": product_name, "price": price, "quantity": quantity})

        await update.message.reply_text(f"✅ Added {quantity}x {product_name} to cart!")
    else:
        await update.message.reply_text("❌ Invalid product selection.")

    return ConversationHandler.END  # End the conversation
async def back_to_categories(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Select a category:", reply_markup=get_category_buttons())
async def product_navigation(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    # Handle "Back to Menu" and "Back to Categories" buttons
    if data == "back_to_menu":
        await back_to_menu(update, context)
        return
    elif data == "back_to_categories":
        await back_to_categories(update, context)
        return

    # Handle product navigation (next/back)
    try:
        action, category_id, position = data.split("_")
        position = int(position)
        user_position[query.from_user.id] = position
        await query.message.edit_reply_markup(reply_markup=get_product_buttons(category_id, position))
    except ValueError as e:
        logger.error(f"Error parsing callback data: {e}")
        await query.answer("An error occurred. Please try again.")
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data["user_id"] = user_id
    await update.message.reply_text(
        "Welcome to our store! Here's how you can navigate:\n"
        "1. Browse through our menu to view products.\n"
        "2. Add items to your cart and proceed to checkout.\n"
        "3. Pay via your preferred method (PayPal, PayFast, or Bitcoin).\n"
        "Click 'Menu' to start shopping.",
        reply_markup=get_main_menu()
    )


async def handle_start_button(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # If the user is a first-time visitor, mark them as no longer a first-timer
    if first_time_users.get(user_id, False):
        first_time_users[user_id] = False  # Mark user as no longer a first-time visitor

        # Send the welcome message and instructions
        await update.message.reply_text(
            "Welcome to our store! Here's how you can navigate:\n"
            "1. Browse through our menu to view products.\n"
            "2. Add items to your cart and proceed to checkout.\n"
            "3. Pay via your preferred method (PayPal, PayFast, or Bitcoin).\n"
            "Click 'Menu' to start shopping.",
            reply_markup=get_main_menu()
        )
    else:
        # If the user is not a first-time visitor, just show the main menu
        await update.message.reply_text("Select an option:", reply_markup=get_main_menu())

async def show_menu(update: Update, context):
    await update.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def category_selected(update: Update, context):
    query = update.callback_query
    category_id = query.data.split("_")[1]
    user_position[query.from_user.id] = 0
    await query.message.edit_text(f"Products in {db_categories[category_id]['name']}",
                                  reply_markup=get_product_buttons(category_id))

async def product_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    _, category_id, product_idx = query.data.split("_")
    product_idx = int(product_idx)

    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, price = products[product_idx]
        user_id = query.from_user.id

        if user_id not in user_cart:
            user_cart[user_id] = []

        # Default quantity to 1
        user_cart[user_id].append({"name": product_name, "price": price, "quantity": 1})

        await query.answer(f"✅ Added 1x {product_name} to cart!")

        # Generate new reply markup
        new_reply_markup = get_product_buttons(category_id, product_idx)

        # Check if the new reply markup is different from the current one
        if new_reply_markup != query.message.reply_markup:
            await query.message.edit_reply_markup(reply_markup=new_reply_markup)
    else:
        await query.answer("❌ Invalid product selection.")

async def view_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await update.message.reply_text("🛒 Your cart is empty.")
        return

    cart_text = "🛒 *Your Cart:*\n"
    keyboard = []

    for idx, item in enumerate(cart_items, start=1):
        cart_text += f"{idx}. {item['quantity']}x {item['name']} - R{item['price'] * item['quantity']}\n"
        # Add a remove button for each item
        keyboard.append([InlineKeyboardButton(f"🗑️ Remove {item['name']}", callback_data=f"remove_{idx-1}")])

    cart_text += "\n🚚 *Delivery Fee:* R100"
    cart_text += f"\n💰 *Total:* R{sum(i['price'] * i['quantity'] for i in cart_items) + 100}"



    await update.message.reply_text(cart_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
async def update_quantity(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    try:
        item_index, new_quantity = update.message.text.strip().split()
        item_index = int(item_index) - 1
        new_quantity = int(new_quantity)

        if 0 <= item_index < len(cart_items) and new_quantity > 0:
            cart_items[item_index]["quantity"] = new_quantity
            await update.message.reply_text(f"✅ Updated {cart_items[item_index]['name']} to {new_quantity}x")
        else:
            await update.message.reply_text("❌ Invalid item number or quantity.")
    except ValueError:
        await update.message.reply_text("❌ Please enter in the format: `ItemNumber NewQuantity`")

    await view_cart(update, context)

async def remove_from_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    # Prevent removal during quantity input
    if context.user_data.get("awaiting_quantity", True):
        await update.message.reply_text("⚠️ Please enter the quantity first before removing an item.")
        return

    try:
        item_index = int(update.message.text.strip()) - 1
        if 0 <= item_index < len(cart_items):
            removed_item = cart_items.pop(item_index)
            await update.message.reply_text(f"🗑️ Removed {removed_item['name']} from cart.")
        else:
            await update.message.reply_text("❌ Invalid item number.")
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")

    await view_cart(update, context)

async def remove_item_callback(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    cart_items = user_cart.get(user_id, [])

    try:
        _, item_index = query.data.split("_")
        item_index = int(item_index)

        if 0 <= item_index < len(cart_items):
            removed_item = cart_items.pop(item_index)
            await query.answer()
            await query.message.edit_text(f"🗑️ Removed {removed_item['name']} from cart.")
        else:
            await query.answer("❌ Invalid item number.")

    except ValueError:
        await query.answer("❌ Error processing your request.")

    await view_cart(update, context)




async def start_shipping(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter your full name:")
    return FULL_NAME

async def full_name(update: Update, context: CallbackContext):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text("Enter your phone number (optional, type 'skip' to continue):")
    return PHONE

async def phone(update: Update, context: CallbackContext):
    phone = update.message.text
    if phone.lower() != "skip":
        context.user_data["phone"] = phone
    else:
        context.user_data["phone"] = None
    await update.message.reply_text("Enter your street address:")
    return ADDRESS

async def address(update: Update, context: CallbackContext):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("Enter your city and postal code:")
    return CITY

async def city(update: Update, context: CallbackContext):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Enter your country:")
    return COUNTRY

async def country(update: Update, context: CallbackContext):
    context.user_data["country"] = update.message.text
    user_info = f"""
📦 **Shipping Address:**
👤 Name: {context.user_data['full_name']}
📞 Phone: {context.user_data['phone'] or 'Not provided'}
🏠 Address: {context.user_data['address']}
🌍 City: {context.user_data['city']}
🌎 Country: {context.user_data['country']}

✅ Confirm? (Yes/No)
"""
    await update.message.reply_text(user_info)
    return CONFIRM

async def confirm(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if update.message.text.lower() == "yes":
        # Store shipping details in user_orders
        user_orders[user_id] = {
            "full_name": context.user_data["full_name"],
            "phone": context.user_data["phone"],
            "address": context.user_data["address"],
            "city": context.user_data["city"],
            "country": context.user_data["country"],
        }

        await update.message.reply_text(
            "✅ Your shipping details have been saved!\n\n"
            "💳 Now you can proceed to payment. or type /pay"
        )

        await update.message.reply_text("✅ Your shipping details have been saved!\n\n💳 Now you can proceed to payment.")
        await update.message.reply_text("Do you have a discount code? (Type 'yes' to enter a code or 'no' to skip):")
        return DISCOUNT_CODE

    else:
        await update.message.reply_text("❌ Shipping details discarded. Start again with /shipping.")
        return ConversationHandler.END


async def handle_discount_code(update: Update, context: CallbackContext):
    user_id = context.user_data.get("user_id")

    if not user_id:
        await update.message.reply_text("⚠ Error: User ID not found. Please restart the process.")
        return ConversationHandler.END

    user_response = update.message.text.strip().lower()

    if user_response == "yes":
        await update.message.reply_text("Please enter your AFFILIATE code:")
        return AFFILIATE_CODE_INPUT
    elif user_response == "no":
        await update.message.reply_text("Please continue with payments by clicking the 'Pay Now' button.",  reply_markup=get_main_menu())
        return PAYMENT_METHOD
    else:
        await update.message.reply_text("Invalid input. Please type 'yes' or 'no'.")
        return DISCOUNT_CODE


async def skip_AFFILIATE(update: Update, context: CallbackContext):
    await update.message.reply_text("Skipping AFFILIATE. Proceeding to payment.")
    await show_payment_methods(update, context)

async def apply_AFFILIATE_code(update: Update, context):
    user_id = context.user_data["user_id"]
    AFFILIATE_code = update.message.text.strip()
    if AFFILIATE_code in AFFILIATE_codes:
        expiry = AFFILIATE_codes[AFFILIATE_code]["expiry"]
        if datetime.now() < expiry:
            user_AFFILIATE_codes[user_id] = AFFILIATE_code
            await update.message.reply_text(f"AFFILIATE code '{AFFILIATE_code}' applied. You will receive a 10% AFFILIATE!")
            await show_payment_methods(update, context)
            return PAYMENT_METHOD
        else:
            await update.message.reply_text("This AFFILIATE code has expired.")
            return AFFILIATE_CODE
    else:
        await update.message.reply_text("Invalid AFFILIATE code. Please try again.")
        return AFFILIATE_CODE


async def show_payment_methods(update: Update, context: CallbackContext):
    logger.info(f"Current state: {context.user_data.get('state')}")
    keyboard = [
        [InlineKeyboardButton("💳 Pay with PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("₿ Pay with Bitcoin", callback_data="pay_bitcoin")],
        [InlineKeyboardButton("💳 Pay with FNB Card", callback_data="pay_fnb")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        # Check if the message content or reply markup has changed
        current_text = update.callback_query.message.text
        current_markup = update.callback_query.message.reply_markup

        new_text = "Select a payment method:"
        if current_text != new_text or current_markup != reply_markup:
            await update.callback_query.edit_message_text(new_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("Select a payment method:", reply_markup=reply_markup)

async def pay_now(update: Update, context: CallbackContext):
    logger.info(f"Current state: {context.user_data.get('state')}")
    user_id = context.user_data.get("user_id")

    if not user_id:
        await update.message.reply_text("Session expired. Please restart with /start.")
        return ConversationHandler.END

    user_data = user_orders.get(user_id, {})

    if not user_data.get("address") or not user_data.get("full_name"):
        await update.message.reply_text(
            "🚚 Please enter your shipping address before proceeding to payment.\n"
            "Use /shipping to provide your details.",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END

    # Transition to PAYMENT_METHOD state
    await show_payment_methods(update, context)
    return PAYMENT_METHOD

async def handle_payment(update: Update, context):
    query = update.callback_query
    user_id = context.user_data["user_id"]
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE  # Include delivery fee

    # Apply 10% discount if affiliate code is present
    if user_id in user_AFFILIATE_codes:
        total_amount *= 0.9
        await query.message.reply_text(f"10% discount applied! New total: R{total_amount:.2f}")

    if query.data == "pay_paypal":
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://example.com/return",
                "cancel_url": "https://example.com/cancel"
            },
            "transactions": [{
                "amount": {"total": f"{total_amount:.2f}", "currency": "USD"},
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
        await query.message.reply_text(f"Please send R{total_amount:.2f} to the following Bitcoin address: {bitcoin_address}")
    elif query.data == "pay_fnb":
        await query.message.reply_text("Please use the following FNB account details for payment:\n\n"
                                       "Bank: FNB\n"
                                       "Account Number: 63086573681\n"
                                       "Branch Code: 250655\n"
                                       "Reference: Your Order Number")
    elif query.data == "back_to_menu":
        await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())

    # Generate and display order number
    order_number = str(uuid.uuid4())[:8]
    user_orders[user_id] = order_number
    await query.message.reply_text(f"Your order number is: {order_number}")

    await query.message.reply_text("Once done, type 'Payment Completed' to confirm.")
    context.user_data["awaiting_payment_confirmation"] = True
    return PAYMENT_CONFIRMATION
    # Notify admin about the order
    admin_message = f"New Order:\nUser ID: {user_id}\nOrder Number: {order_number}\nTotal Amount: R{total_amount:.2f}"
    await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

    return ConversationHandler.END



async def payment_confirmation(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()

    # Get user_id safely
    user_id = context.user_data.get("user_id")
    if not user_id:
        await update.message.reply_text("⚠ Error: User ID not found. Please restart the payment process.")
        return ConversationHandler.END

    # Check if the user confirmed payment
    if user_input == "payment completed":
        # Simulate payment validation (replace with actual logic)
        is_valid = await validate_payment(update, context)

        if is_valid:
            # Generate a unique order number
            order_number = str(uuid.uuid4())[:8]
            user_orders[user_id] = order_number  # Store the order number

            # Notify the user
            await update.message.reply_text(f"✅ Payment confirmed!")

            # Notify the admin
            admin_message = f"🛒 New Order:\n👤 User ID: {user_id}\n📦 Order Number: {order_number}"
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

            # Ask the user what they want to do next
            await update.message.reply_text(
                "What would you like to do next?\n"
                "1. Type 'continue' to continue shopping.\n"
                "2. Type 'track' to track your order.\n"
                "3. Type 'exit' to end the conversation."
            )

            # Transition to the NEXT_STEP state
            return NEXT_STEP

        else:
            # Payment validation failed
            await update.message.reply_text("❌ Payment validation failed. Please try again.")
            return PAYMENT_CONFIRMATION

    else:
        # User did not confirm payment
        await update.message.reply_text(
            "⚠ Payment not confirmed. Please type 'Payment Completed' once payment is done."
        )
        return PAYMENT_CONFIRMATION
async def validate_payment(update: Update, context: CallbackContext):
    return True

async def handle_user_choice(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    user_id = context.user_data.get("user_id")
    order_number = user_orders.get(user_id)

    if user_input == "continue":
        await update.message.reply_text("Continuing your shopping... 🎉\nChoose what you'd like to buy next.")
        return ConversationHandler.END
    elif user_input == "track":
        if order_number:
            await update.message.reply_text(f"Your order number is: {order_number}. Tracking details will be sent soon.")
        else:
            await update.message.reply_text("Sorry, we couldn't find your order. Please try again later.")
        return ConversationHandler.END
    elif user_input == "exit":
        await update.message.reply_text("Thank you for using our service. Goodbye! 👋")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid input. Please type 'continue', 'track', or 'exit'.")
        return NEXT_STEP

async def cancel_payment(update: Update, context: CallbackContext):
    await update.message.reply_text("Payment process canceled. Returning to the main menu.", reply_markup=get_main_menu())
    return ConversationHandler.END

shipping_conversation = ConversationHandler(
    entry_points=[CommandHandler("shipping", start_shipping)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
        COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        DISCOUNT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discount_code)],
    },
    fallbacks=[],
)

# Payment Conversation Handler
payment_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now)],
    states={
        AFFILIATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discount_code)],
        AFFILIATE_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_AFFILIATE_code)],
        PAYMENT_METHOD: [CallbackQueryHandler(handle_payment, pattern="^(pay_paypal|pay_bitcoin|pay_fnb|back_to_menu)$")],
        PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel_payment)],
)




# Add the payment conversation handler to the application

async def help(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Here's how you can use the bot:\n"
        "1. Use /start to begin.\n"
        "2. Click '🛍 Menu' to browse products.\n"
        "3. Add items to your cart and proceed to checkout.\n"
        "4. Pay via your preferred method (PayPal, Bitcoin, or FNB Card).\n"
        "5. Track your order or continue shopping after payment."
    )

async def about(update: Update, context: CallbackContext):
    await update.message.reply_text("This is a sample Telegram bot for an online store.")
async def back_to_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Returning to the main menu.", reply_markup=get_main_menu())


async def support(update: Update, context: CallbackContext):
    await update.message.reply_text("Contact support at support@example.com.")

application = Application.builder().token(TOKEN).build()



# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶ Start$"), handle_start_button))
application.add_handler(payment_conv_handler)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Skip"), skip_AFFILIATE))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(CallbackQueryHandler(category_selected, pattern="category_.*"))
application.add_handler(CallbackQueryHandler(product_selected, pattern="add_.*"))
application.add_handler(CallbackQueryHandler(product_navigation, pattern="(next|back)_.*"))
application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
application.add_handler(CallbackQueryHandler(back_to_categories, pattern="back_to_categories"))
application.add_handler(shipping_conversation)
application.add_handler(CallbackQueryHandler(set_quantity, pattern=r"^set_quantity_\d+_\d+$"))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+\s+\d+$") & ~filters.COMMAND, update_quantity))



# Create ConversationHandler for setting quantity
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_quantity, pattern=r"^set_quantity_\d+_\d+$")],
    states={
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity)]
    },
    fallbacks=[]
)

application.add_handler(conv_handler)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, remove_from_cart))  # Keep cart removal separate
application.add_handler(CallbackQueryHandler(remove_item_callback, pattern=r"^remove_\d+$"))






# Start the bot
if __name__ == "__main__":
    application.run_polling()