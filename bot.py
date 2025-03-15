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
(FULL_NAME, PHONE, ADDRESS, CITY, COUNTRY, CONFIRM, DISCOUNT_CODE, AFFILIATE_CODE_INPUT,
 PAYMENT_METHOD, PAYMENT_CONFIRMATION, NEXT_STEP, REMOVE_PRODUCT, REMOVE_QUANTITY) = range(13)

db_categories = {
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60, "Product3": 70, "Product4": 80, "Product5": 90, "Product6": 100, "Product7": 110, "Product8": 120}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70, "Product3": 75, "Product4": 85, "Product5": 95, "Product6": 105, "Product7": 115, "Product8": 125}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80, "Product3": 85, "Product4": 95, "Product5": 105, "Product6": 115, "Product7": 125, "Product8": 135}},
}
# Helper functions

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🛍 Menu"), KeyboardButton("🛒 View Cart")],
            [KeyboardButton("💳 Pay Now"), KeyboardButton("Track Order")],
            [KeyboardButton("ℹ About"), KeyboardButton("❓ Help"), KeyboardButton("📞 Support")]
        ], resize_keyboard=True
    )
def get_start_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("▶ Start")]
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
        buttons.append([
            InlineKeyboardButton(f"🛒 {product} - R{price}", callback_data=f"add_{category_id}_{product_idx}"),
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

# Start command
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    first_time_users[user_id] = True  # Mark user as first-time visitor

    await update.message.reply_text(
        "Welcome to our store! Here's how you can navigate:\n"
        "1. Browse through our menu to view products.\n"
        "2. Add items to your cart and proceed to checkout.\n"
        "3. Pay via your preferred method (PayPal, Bitcoin, or Credit Card).\n"
        "4. Track your order after payment.\n"
        "Click '▶ MENU' to begin.",
        reply_markup=get_start_menu()
    )

# Handle Start button
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
            "3. Pay via your preferred method (PayPal, Bitcoin, or FNB Card).\n"
            "4. Track your order after payment.\n"
            "Click '🛍 Menu' to start shopping.",
            reply_markup=get_main_menu()
        )
    else:
        # If the user is not a first-time visitor, just show the main menu
        await update.message.reply_text("Select an option:", reply_markup=get_main_menu())

# Menu command
async def show_menu(update: Update, context: CallbackContext):
    await update.message.reply_text("Select a category:", reply_markup=get_category_buttons())

# Category selected
async def category_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    category_id = query.data.split("_")[1]
    await query.message.edit_text(f"Products in {db_categories[category_id]['name']}",
                                  reply_markup=get_product_buttons(category_id))

# Product selected
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

# View cart
async def view_cart(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await update.message.reply_text("🛒 Your cart is empty.", reply_markup=get_main_menu())
        return

    cart_text = "🛒 *Your Cart:*\n"
    for idx, item in enumerate(cart_items, start=1):
        cart_text += f"{idx}. {item['quantity']}x {item['name']} - R{item['price'] * item['quantity']}\n"

    cart_text += "\n🚚 *Delivery Fee:* R100"
    cart_text += f"\n💰 *Total:* R{sum(i['price'] * i['quantity'] for i in cart_items) + 100}"

    # Add "Pay Now" and "Remove Item" buttons
    keyboard = [
        # [InlineKeyboardButton("💳 Pay Now", callback_data="pay_now")],
        [InlineKeyboardButton("🗑️ Remove Item", callback_data="remove_item")]
    ]
    await update.message.reply_text(cart_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# Set quantity
async def set_quantity(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    logger.info(f"set_quantity triggered with callback_data: {callback_data}")

    try:
        _, _, category_id, product_idx = callback_data.split("_")
        product_idx = int(product_idx)
    except ValueError:
        logger.error("Invalid data format in set_quantity")
        await query.answer("❌ Invalid data format. Please try again.")
        return

    context.user_data["selected_product"] = (category_id, product_idx)
    context.user_data["awaiting_quantity"] = True  # Set flag

    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, _ = products[product_idx]
        await query.answer()
        logger.info(f"Prompting user to enter quantity for product: {product_name}")
        await query.message.reply_text(f"📝 Enter the number of quantity/products you want for {product_name}:")

    logger.info(f"Transitioning to ENTER_QUANTITY state")
    return ENTER_QUANTITY  # Move to quantity input step
async def enter_quantity(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    quantity = update.message.text.strip()

    logger.info(f"enter_quantity triggered with quantity: {quantity}")
    logger.info(f"Current state: {context.user_data}")

    if not quantity.isdigit() or int(quantity) <= 0:
        logger.warning(f"Invalid quantity entered: {quantity}")
        await update.message.reply_text("❌ Invalid quantity. Please enter a positive number:")
        return ENTER_QUANTITY

    quantity = int(quantity)
    selected_product = context.user_data.get("selected_product")
    if not selected_product:
        logger.error("No selected_product found in context.user_data")
        await update.message.reply_text("❌ Something went wrong. Please try again.")
        return ConversationHandler.END

    category_id, product_idx = selected_product
    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, price = products[product_idx]

        if user_id not in user_cart:
            user_cart[user_id] = []

        existing_item = next((item for item in user_cart[user_id] if item["name"] == product_name), None)

        if existing_item:
            existing_item["quantity"] += quantity  # Update quantity
            logger.info(f"Updated quantity for {product_name} to {existing_item['quantity']}")
        else:
            user_cart[user_id].append({"name": product_name, "price": price, "quantity": quantity})
            logger.info(f"Added {quantity}x {product_name} to cart")

        await update.message.reply_text(f"✅ Set {quantity}x {product_name} in cart!", reply_markup=get_main_menu())
    else:
        logger.error(f"Invalid product selection: category_id={category_id}, product_idx={product_idx}")
        await update.message.reply_text("❌ Invalid product selection.")

    logger.info("Ending conversation")
    return ConversationHandler.END
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

async def remove_item_callback(update: Update, context: CallbackContext):
    """Ask the user which product they want to remove."""
    query = update.callback_query
    user_id = query.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await query.answer("🛒 Your cart is empty.")
        return ConversationHandler.END

    # Display cart items for selection
    cart_text = "\n".join(
        [f"{i + 1}. {item['quantity']}x {item['name']} - R{item['price']}" for i, item in enumerate(cart_items)])

    await query.message.edit_text(
        f"🗑️ Select the product number to remove:\n{cart_text}\n\nSend the product number:"
    )

    return REMOVE_PRODUCT  # Move to next step
async def remove_product(update: Update, context: CallbackContext):
    """Process product selection and check quantity."""
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    product_number_text = update.message.text.strip()

    if not product_number_text.isdigit():
        await update.message.reply_text("❌ Please enter a valid product number.")
        return REMOVE_PRODUCT  # Ask again

    product_number = int(product_number_text) - 1  # Convert to index

    if product_number < 0 or product_number >= len(cart_items):
        await update.message.reply_text("❌ Invalid product number. Try again.")
        return REMOVE_PRODUCT  # Ask again

    selected_item = cart_items[product_number]
    context.user_data["remove_item_index"] = product_number

    # If more than 1 quantity, ask how many to remove
    if selected_item["quantity"] > 1:
        await update.message.reply_text(
            f"📝 You have {selected_item['quantity']}x {selected_item['name']} in your cart.\n"
            "How many would you like to remove?",reply_markup=get_main_menu()
        )
        return REMOVE_QUANTITY  # Move to next step

    # If only 1, remove immediately
    removed_item = cart_items.pop(product_number)
    await update.message.reply_text(f"🗑️ Removed {removed_item['name']} (1x) from cart.",reply_markup=get_main_menu())
    await view_cart(update, context)

    return ConversationHandler.END  # End conversation
async def remove_quantity(update: Update, context: CallbackContext):
    """Remove the specified quantity from the cart."""
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    item_index = context.user_data.get("remove_item_index")

    if item_index is None or item_index >= len(cart_items):
        await update.message.reply_text("❌ Something went wrong. Please try again.",reply_markup=get_main_menu())
        return ConversationHandler.END

    selected_item = cart_items[item_index]
    remove_qty_text = update.message.text.strip()

    # Validate input
    if not remove_qty_text.isdigit() or int(remove_qty_text) <= 0:
        await update.message.reply_text("❌ Please enter a valid quantity to remove.",reply_markup=get_main_menu())
        return REMOVE_QUANTITY  # Ask again

    remove_qty = int(remove_qty_text)

    if remove_qty >= selected_item["quantity"]:
        # Remove entire item if removing equal or more than available quantity
        removed_item = cart_items.pop(item_index)
        await update.message.reply_text(f"🗑️ Removed {removed_item['name']} ({removed_item['quantity']}x) from cart.")
    else:
        # Decrease quantity
        selected_item["quantity"] -= remove_qty
        await update.message.reply_text(f"🗑️ Removed {selected_item['name']} ({remove_qty}x) from cart.")

    await view_cart(update, context)
    return ConversationHandler.END  # End conversation

# Shipping conversation
async def start_shipping(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter your full name:")
    return FULL_NAME

async def full_name(update: Update, context: CallbackContext):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text("Please enter your phone number:")
    return PHONE

async def phone(update: Update, context: CallbackContext):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Please enter your address:")
    return ADDRESS

async def address(update: Update, context: CallbackContext):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("Please enter your city:")
    return CITY

async def city(update: Update, context: CallbackContext):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Please enter your country:")
    return COUNTRY

async def country(update: Update, context: CallbackContext):
    context.user_data["country"] = update.message.text
    user_id = update.message.from_user.id

    # Display shipping details for confirmation
    shipping_details = (
        f"📦 **Shipping Address:**\n"
        f"👤 Name: {context.user_data['full_name']}\n"
        f"📞 Phone: {context.user_data['phone']}\n"
        f"🏠 Address: {context.user_data['address']}\n"
        f"🌍 City: {context.user_data['city']}\n"
        f"🌎 Country: {context.user_data['country']}\n\n"
        "✅ Confirm? (Yes/No)"
    )
    await update.message.reply_text(shipping_details)
    return CONFIRM

async def confirm_shipping(update: Update, context: CallbackContext):
    user_response = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    if user_response == "yes":
        # Save shipping details to user_orders
        user_orders[user_id] = {
            "full_name": context.user_data["full_name"],
            "phone": context.user_data["phone"],
            "address": context.user_data["address"],
            "city": context.user_data["city"],
            "country": context.user_data["country"]
        }

        await update.message.reply_text("✅ Your shipping details have been saved!")

        # Check if the cart is empty
        cart_items = user_cart.get(user_id, [])
        if not cart_items:
            await update.message.reply_text("🛒 Your cart is empty. Add items to proceed to payment.", reply_markup=get_main_menu())
            return ConversationHandler.END

        # Ask if the user has a discount code
        await update.message.reply_text("Do you have a discount code? (yes/no)")
        return DISCOUNT_CODE  # Move to discount code step
    elif user_response == "no":
        await update.message.reply_text("Please re-enter your shipping details.")
        return FULL_NAME  # Restart the shipping process
    else:
        await update.message.reply_text("Invalid input. Please type 'yes' or 'no'.")
        return CONFIRM  # Stay in the CONFIRM state

async def cancel_shipping(update: Update, context: CallbackContext):
    await update.message.reply_text("Shipping process canceled. Returning to the main menu.", reply_markup=get_main_menu())
    return ConversationHandler.END




# Payment conversation
async def start_payment(update: Update, context: CallbackContext):
    logger.info("start_payment triggered")

    # Determine if the update is from a callback query or a message
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        logger.info("Triggered by inline keyboard button")
    else:
        user_id = update.message.from_user.id
        logger.info("Triggered by reply keyboard button")

    context.user_data["user_id"] = user_id

    # Check if the cart is empty
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        if update.callback_query:
            await update.callback_query.message.reply_text("🛒 Your cart is empty. Add items to proceed to payment.")
        else:
            await update.message.reply_text("🛒 Your cart is empty. Add items to proceed to payment.")
        return

    # Check if shipping details are saved
    user_data = user_orders.get(user_id, {})
    if not user_data.get("address") or not user_data.get("full_name"):
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "🚚 Please provide your shipping details before proceeding to payment.\n"
                "Use /shipping to provide your details.",
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text(
                "🚚 Please provide your shipping details before proceeding to payment.\n"
                "Use /shipping to provide your details.",
                reply_markup=get_main_menu()
            )
        return

    # Ask if the user has a discount code
    if update.callback_query:
        await update.callback_query.message.reply_text("Do you have a discount code? (yes/no)")
    else:
        await update.message.reply_text("Do you have a discount code? (yes/no)")
    return DISCOUNT_CODE
async def handle_discount_code(update: Update, context: CallbackContext):
    user_response = update.message.text.strip().lower()

    if user_response == "yes":
        await update.message.reply_text("Please enter your discount code:")
        return AFFILIATE_CODE_INPUT
    elif user_response == "no":
        await update.message.reply_text("Proceeding to payment methods.")
        await show_payment_methods(update, context)
        return PAYMENT_METHOD
    else:
        await update.message.reply_text("Invalid input. Please type 'yes' or 'no'.")
        return DISCOUNT_CODE

async def apply_AFFILIATE_code(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    AFFILIATE_code = update.message.text.strip()

    if AFFILIATE_code in AFFILIATE_codes:
        expiry = AFFILIATE_codes[AFFILIATE_code]["expiry"]
        if datetime.now() < expiry:
            user_AFFILIATE_codes[user_id] = AFFILIATE_code
            await update.message.reply_text(f"Discount code '{AFFILIATE_code}' applied. You will receive a 10% discount!")
            await show_payment_methods(update, context)
            return PAYMENT_METHOD
        else:
            await update.message.reply_text("This discount code has expired.")
            return AFFILIATE_CODE_INPUT
    else:
        await update.message.reply_text("Invalid discount code. Please try again.")
        return AFFILIATE_CODE_INPUT

async def show_payment_methods(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💳 Pay with PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("₿ Pay with Bitcoin", callback_data="pay_bitcoin")],
        [InlineKeyboardButton("💳 Pay with FNB Card", callback_data="pay_fnb")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.reply_text("Select a payment method:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Select a payment method:", reply_markup=reply_markup)

    return PAYMENT_METHOD

async def handle_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query to stop the loading animation

    logger.info(f"handle_payment triggered with callback_data: {query.data}")

    user_id = query.from_user.id
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items) + DELIVERY_FEE

    # Apply discount if applicable
    if user_id in user_AFFILIATE_codes:
        total_amount *= 0.9
        await query.message.reply_text(f"10% discount applied! New total: R{total_amount:.2f}")

    if query.data == "pay_paypal":
        logger.info("User selected PayPal payment method")
        await query.message.reply_text("Redirecting to PayPal... (Simulated)")
    elif query.data == "pay_bitcoin":
        logger.info("User selected Bitcoin payment method")
        await query.message.reply_text(f"Please send R{total_amount:.2f} to the following Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    elif query.data == "pay_fnb":
        logger.info("User selected FNB payment method")
        await query.message.reply_text("Please use the following FNB account details for payment:\n\n"
                                      "Bank: FNB\n"
                                      "Account Number: 63086573681\n"
                                      "Branch Code: 250655\n"
                                      "Reference: Your Order Number")
    elif query.data == "back_to_menu":
        logger.info("User selected Back to Menu")
        await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())
        return ConversationHandler.END

    # Generate and display order number
    order_number = str(uuid.uuid4())[:8]
    user_orders[user_id] = {
        "order_number": order_number,
        "status": "Pending",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **user_orders.get(user_id, {})  # Include shipping details
    }
    await query.message.reply_text(f"Your order number is: {order_number}")

    await query.message.reply_text("Once done, type 'Payment Completed' to confirm.")
    context.user_data["awaiting_payment_confirmation"] = True
    return PAYMENT_CONFIRMATION

async def payment_confirmation(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    if user_input == "payment completed":
        # Clear the cart
        user_cart[user_id] = []
        await update.message.reply_text("✅ Payment confirmed! Your cart has been cleared.")

        # Notify admin
        order_number = user_orders[user_id]["order_number"]
        admin_message = f"🛒 New Order:\n👤 User ID: {user_id}\n📦 Order Number: {order_number}"
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

        # Ask the user what they want to do next
        await update.message.reply_text(
            "What would you like to do next?\n"
            "1. Type 'continue' to continue shopping.\n"
            "2. Type 'track' to track your order.\n"
            "3. Type 'exit' to end the conversation."
        )
        return NEXT_STEP
    else:
        await update.message.reply_text("⚠ Payment not confirmed. Please type 'Payment Completed' once payment is done.")
        return PAYMENT_CONFIRMATION

async def handle_user_choice(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    user_id = update.message.from_user.id
    order_info = user_orders.get(user_id)

    if user_input == "continue":
        await update.message.reply_text("Continuing your shopping... 🎉\nChoose what you'd like to buy next.")
        return ConversationHandler.END
    elif user_input == "track":
        if order_info:
            await update.message.reply_text(f"Your order number is: {order_info['order_number']}\n"
                                           f"Status: {order_info['status']}\n"
                                           f"Date: {order_info['date']}")
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



async def back_to_categories(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def back_to_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Returning to the main menu.", reply_markup=get_main_menu())

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

# Help command
async def help(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Here's how you can use the bot:\n"
        "1. Use /start to begin.\n"
        "2. Click '🛍 Menu' to browse products.\n"
        "3. Add items to your cart and proceed to checkout.\n"
        "4. Pay via your preferred method (PayPal, Bitcoin, or FNB Card).\n"
        "5. Track your order or continue shopping after payment.\n"
        "Commands:\n"
        "- /start: Start the bot.\n"
        "- /help: Show this help message.\n"
        "- /shipping: Enter shipping details.\n"
        "- /pay: Start the payment process.\n"
        "- /track: Track your order."
    )

# About command
async def about(update: Update, context: CallbackContext):
    await update.message.reply_text("This is a sample Telegram bot for an online store.")

# Support command
async def support(update: Update, context: CallbackContext):
    await update.message.reply_text("Contact support at support@example.com.")

# Track order
async def track_order(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    order_info = user_orders.get(user_id)

    if order_info:
        await update.message.reply_text(
            f"📦 **Your Order:**\n"
            f"🔢 Order Number: {order_info['order_number']}\n"
            f"📅 Date: {order_info['date']}\n"
            f"📦 Status: {order_info['status']}"
        )
    else:
        await update.message.reply_text("You have no orders to track.")

# View cart
async def view_cart(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await update.message.reply_text("🛒 Your cart is empty.", reply_markup=get_main_menu())
        return

    cart_text = "🛒 *Your Cart:*\n"
    for idx, item in enumerate(cart_items, start=1):
        cart_text += f"{idx}. {item['quantity']}x {item['name']} - R{item['price'] * item['quantity']}\n"

    cart_text += "\n🚚 *Delivery Fee:* R100"
    cart_text += f"\n💰 *Total:* R{sum(i['price'] * i['quantity'] for i in cart_items) + 100}"

    # Add "Pay Now" and "Remove Item" buttons
    keyboard = [
        # [InlineKeyboardButton("💳 Pay Now", callback_data="pay_now")],
        [InlineKeyboardButton("🗑️ Remove Item", callback_data="remove_item")]
    ]
    await update.message.reply_text(cart_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# Shipping Conversation Handler
shipping_conversation = ConversationHandler(
    entry_points=[CommandHandler("shipping", start_shipping)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
        COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_shipping)],
    },
    fallbacks=[CommandHandler("cancel", cancel_shipping)],
)

# Payment Conversation Handler
payment_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_payment, pattern="^pay_now$"),  # For inline keyboard button
        MessageHandler(filters.TEXT & filters.Regex("^💳 Pay Now$"), start_payment)  # For reply keyboard button
    ],
    states={
        DISCOUNT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discount_code)],
        AFFILIATE_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_AFFILIATE_code)],
        PAYMENT_METHOD: [
            CallbackQueryHandler(handle_payment, pattern="^(pay_paypal|pay_bitcoin|pay_fnb|back_to_menu)$")
        ],
        PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel_payment)],
)
# Quantity Conversation Handler
quantity_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_quantity, pattern="^set_quantity_")],
    states={
        ENTER_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity),
        ],
    },
    fallbacks=[],
)
logger.info("Quantity Conversation Handler set up")

# Add conversation handler for removing items
remove_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(remove_item_callback, pattern="^remove_item$")],
    states={
        REMOVE_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_product)],
        REMOVE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_quantity)],
    },
    fallbacks=[],
)


# Main bot setup
# Main bot setup
application = Application.builder().token(TOKEN).build()

# Add conversation handlers first
application.add_handler(quantity_conv_handler)
application.add_handler(shipping_conversation)
application.add_handler(payment_conv_handler)
application.add_handler(remove_conversation_handler)

# Add other handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶ Start$"), handle_start_button))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛍 Menu$"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛒 View Cart$"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Track Order$"), track_order))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^❓ Help$"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^ℹ About$"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📞 Support$"), support))
application.add_handler(CallbackQueryHandler(category_selected, pattern="^category_.*"))
application.add_handler(CallbackQueryHandler(product_selected, pattern="^add_.*"))
application.add_handler(CallbackQueryHandler(set_quantity, pattern="^set_quantity_.*"))
application.add_handler(CallbackQueryHandler(remove_item_callback, pattern="^remove_item$"))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💳 Pay Now$"), start_payment))
application.add_handler(CommandHandler("pay", start_payment))
application.add_handler(CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"))
application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
application.add_handler(CallbackQueryHandler(product_navigation, pattern="^(next|back)_.*"))

# Start the bot
if __name__ == "__main__":
    application.run_polling()