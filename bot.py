import logging

from ccxt import BadRequest
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, \
    ConversationHandler, CallbackContext
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
    "1": {"name": "GREENHOUSE", "products": {"Mimosa": 90, "White Truffle": 60, "Product3": 70, "Product4": 80, "Product5": 90, "Product6": 100, "Product7": 110, "Product8": 120}},
    "2": {"name": "GREENDOOR", "products": {"Sunset Sherbet": 85, "Purple Punch": 70, "Product3": 75, "Product4": 85, "Product5": 95, "Product6": 105, "Product7": 115, "Product8": 125}},
    "3": {"name": "TUNNEL AA", "products": {"Gelato": 95, "Wedding Cake": 80, "Product3": 85, "Product4": 95, "Product5": 105, "Product6": 115, "Product7": 125, "Product8": 135}},
}

# User Cart Storage
user_cart = {}
user_position = {}
user_orders = {}
user_AFFILIATE_codes = {}

# AFFILIATE Codes Storage
AFFILIATE_codes = {}  # Format: {"code": {"expiry": datetime, "AFFILIATE": 0.1}}

# Delivery Fee
DELIVERY_FEE = 100  # Default delivery fee of R100

# Conversation states
AFFILIATE_CODE,AFFILIATE_CODE_INPUT, PAYMENT_METHOD, ADD_PRODUCT, REMOVE_PRODUCT, GENERATE_CODE = range(6)

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
    keyboard = [[KeyboardButton("▶ Start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to our store! Click 'Start' to continue.", reply_markup=reply_markup)

async def handle_start_button(update: Update, context):
    await update.message.reply_text("Select an option:", reply_markup=get_main_menu())

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

    # Get new inline keyboard markup
    new_reply_markup = get_product_buttons(category_id, position)

    # Only edit message if the markup is different
    if query.message.reply_markup != new_reply_markup:
        try:
            await query.message.edit_reply_markup(reply_markup=new_reply_markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                print("Skipping edit: Message is already up-to-date.")
            else:
                raise  # Re-raise unexpected errors
    else:
        print("Skipping update: No changes in reply markup.")
async def view_cart(update: Update, context):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if not cart_items:
        await update.message.reply_text("Your cart is empty.")
        return
    cart_details = "\n".join([f"{idx + 1}. {item['name']} - R{item['price']}" for idx, item in enumerate(cart_items)])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE
    await update.message.reply_text(f"Your Cart:\n{cart_details}\n\nDelivery Fee: R{DELIVERY_FEE}\nTotal: R{total_amount}\n\nReply with the item number to remove it.",
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


#Address conversation

# Define conversation states
FULL_NAME, PHONE, ADDRESS, CITY, COUNTRY, CONFIRM,PAYMENT_CONFIRMATION, AFFILIATE_CODE, NEXT_STEP = range(9)


async def start_shipping(update: Update, context: CallbackContext):
    """Start collecting the user's shipping details."""
    await update.message.reply_text("Please enter your full name:")
    return FULL_NAME

async def full_name(update: Update, context: CallbackContext):
    """Ask for phone number after getting full name."""
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text("Enter your phone number (optional, type 'skip' to continue):")
    return PHONE

async def phone(update: Update, context: CallbackContext):
    """Ask for address after phone number."""
    phone = update.message.text
    if phone.lower() != "skip":
        context.user_data["phone"] = phone
    else:
        context.user_data["phone"] = None

    await update.message.reply_text("Enter your street address:")
    return ADDRESS

async def address(update: Update, context: CallbackContext):
    """Ask for city and postal code."""
    context.user_data["address"] = update.message.text
    await update.message.reply_text("Enter your city and postal code:")
    return CITY

async def city(update: Update, context: CallbackContext):
    """Ask for country."""
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Enter your country:")
    return COUNTRY

async def country(update: Update, context: CallbackContext):
    """Confirm details before saving."""
    context.user_data["country"] = update.message.text

    # Show a summary of the user's input
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
    """Save the shipping details if the user confirms and redirect to payment."""
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
            "💳 Now you can proceed to payment."
        )

        # Now proceed to handle affiliate code
        await update.message.reply_text("Do you have a discount code? (Type 'yes' to enter a code or 'no' to skip):")
        return AFFILIATE_CODE  # Transition to affiliate code state

    else:
        await update.message.reply_text("❌ Shipping details discarded. Start again with /shipping.")
        return ConversationHandler.END

async def skip_AFFILIATE(update: Update, context):
    await update.message.reply_text("Skipping AFFILIATE. Proceeding to payment.")
    await show_payment_methods(update, context)

async def pay_now(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data["user_id"] = user_id  # ✅ Ensure user_id is stored

    # Ensure the user has provided shipping details
    user_data = user_orders.get(user_id, {})  # Get user data or empty dict

    if not user_data.get("address") or not user_data.get("full_name"):
        await update.message.reply_text(
            "🚚 Please enter your shipping address before proceeding to payment.\n"
            "Use /shipping to provide your details.",
            reply_markup= get_main_menu()  # ✅ Add main menu keyboard
        )
        return ConversationHandler.END  # End the conversation if no shipping details

    await update.message.reply_text("Do you have an AFFILIATE code? (Type 'yes' to enter a code or 'no' to skip):")
    return AFFILIATE_CODE  # ✅ Correctly transition to affiliate code step


#User's AFFILIATE code
async def handle_AFFILIATE_code(update: Update, context: CallbackContext):
    user_id = context.user_data.get("user_id")

    if not user_id:
        await update.message.reply_text("⚠ Error: User ID not found. Please restart the process.")
        return ConversationHandler.END  # End conversation safely

    user_response = update.message.text.strip().lower()

    if user_response == "yes":
        await update.message.reply_text("Please enter your AFFILIATE code:")
        return AFFILIATE_CODE_INPUT  # ✅ Correctly transition to input state

    elif user_response == "no":
        await update.message.reply_text("No discount code applied. Proceeding to payment.")
        await show_payment_methods(update, context)
        return PAYMENT_METHOD  # ✅ Ensure state transition

    else:
        await update.message.reply_text("Invalid input. Please type 'yes' or 'no'.")
        return AFFILIATE_CODE


# Define the ConversationHandler
shipping_conversation = ConversationHandler(
    entry_points=[CommandHandler("shipping", start_shipping)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
        COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        AFFILIATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_AFFILIATE_code)],

        # Ensure correct state value
    },
    fallbacks=[],
)

async def apply_AFFILIATE_code(update: Update, context):
    user_id = context.user_data["user_id"]
    AFFILIATE_code = update.message.text.strip()

    # Validate the AFFILIATE code
    if AFFILIATE_code in AFFILIATE_codes:
        expiry = AFFILIATE_codes[AFFILIATE_code]["expiry"]
        if datetime.now() < expiry:
            user_AFFILIATE_codes[user_id] = AFFILIATE_code
            await update.message.reply_text(f"AFFILIATE code '{AFFILIATE_code}' applied. You will receive a 10% AFFILIATE!")
            await show_payment_methods(update, context)
            return PAYMENT_METHOD  # Transition to PAYMENT_METHOD state
        else:
            await update.message.reply_text("This AFFILIATE code has expired.")
            return AFFILIATE_CODE  # Stay in AFFILIATE_CODE state
    else:
        await update.message.reply_text("Invalid AFFILIATE code. Please try again.")
        return AFFILIATE_CODE  # Stay in AFFILIATE_CODE state

async def show_payment_methods(update: Update, context):
    await update.message.reply_text(
        "Select a payment method:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay with PayPal", callback_data="pay_paypal")],
            [InlineKeyboardButton("₿ Pay with Bitcoin", callback_data="pay_bitcoin")],
            [InlineKeyboardButton("💳 Pay with FNB Card", callback_data="pay_fnb")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ])
    )



# Ensure your payment methods are correctly handled
async def handle_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Log the callback data for debugging
    print(f"Callback data received: {query.data}")

    user_id = context.user_data["user_id"]
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE

    # Apply 10% AFFILIATE if AFFILIATE code is present
    if user_id in user_AFFILIATE_codes:
        total_amount *= 0.9  # Apply a 10% discount if affiliate code is found
        await query.message.reply_text(f"10% AFFILIATE applied! New total: R{total_amount:.2f}")

    # Handle PayPal payment
    if query.data == "pay_paypal":
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://example.com/return",  # Replace with your actual return URL
                "cancel_url": "https://example.com/cancel"  # Replace with your actual cancel URL
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
                    await query.message.reply_text(f"Please proceed with your PayPal payment: {redirect_url}")
                    break
        else:
            logger.error(f"PayPal Payment Creation Failed: {payment.error}")
            await query.message.reply_text("Payment creation failed. Please try again.")
            return ConversationHandler.END  # Exit conversation on failure

        await query.message.reply_text(
            "Once done, type 'Payment Completed' to confirm."
        )

        # Flag that the user is awaiting payment confirmation
        context.user_data["awaiting_payment_confirmation"] = True
        return PAYMENT_CONFIRMATION

    # Handle Bitcoin payment
    elif query.data == "pay_bitcoin":
        bitcoin_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Replace with your Bitcoin address
        await query.message.reply_text(
            f"Please send R{total_amount:.2f} to the following Bitcoin address:\n{bitcoin_address}\n\n"
            "Once done, type 'Payment Completed' to confirm."
        )

        # Flag that the user is awaiting payment confirmation
        context.user_data["awaiting_payment_confirmation"] = True
        return PAYMENT_CONFIRMATION

    # Handle FNB payment
    elif query.data == "pay_fnb":
        await query.message.reply_text(
            "Please use the following FNB account details for payment:\n\n"
            "Bank: FNB\n"
            "Account Number: 63086573681\n"
            "Branch Code: 250655\n"
            "Reference: Your Order Number\n\n"
            "Once done, type 'Payment Completed' to confirm."
        )

        # Flag that the user is awaiting payment confirmation
        context.user_data["awaiting_payment_confirmation"] = True
        return PAYMENT_CONFIRMATION

    # Go back to main menu
    elif query.data == "back_to_menu":
        await query.message.reply_text("Returning to the main menu.", reply_markup=get_main_menu())
        return ConversationHandler.END  # End the conversation if going back to the menu

    else:
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        return PAYMENT_METHOD  # Return to the payment method selection state

async def payment_confirmation(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()

    # Get user_id safely
    user_id = context.user_data.get("user_id")  # Use .get() to avoid KeyError

    if not user_id:
        await update.message.reply_text("⚠ Error: User ID not found. Please restart the payment process.")
        return ConversationHandler.END  # Exit conversation safely

    if user_input == "payment completed":
        is_valid = await validate_payment(update, context)

        if is_valid:
            order_number = str(uuid.uuid4())[:8]
            user_orders[user_id] = order_number  # ✅ Safe assignment

            await update.message.reply_text(f"✅ Payment confirmed!\nYour order number is: {order_number}")

            admin_message = f"🛒 New Order:\n👤 User ID: {user_id}\n📦 Order Number: {order_number}"
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

            # Ask if they want to continue, track the order, or exit
            await update.message.reply_text(
                "What would you like to do next?\n"
                "1. Type 'continue' to continue shopping.\n"
                "2. Type 'track' to track your order.\n"
                "3. Type 'exit' to end the conversation."
            )

            # Return a new state to handle the user's response
            return NEXT_STEP  # Define this state to handle their choice

        else:
            await update.message.reply_text("❌ Payment validation failed. Please try again.")
            return PAYMENT_CONFIRMATION
    else:
        await update.message.reply_text(
            "⚠ Payment not confirmed. Please type 'Payment Completed' once payment is done."
        )
        return PAYMENT_CONFIRMATION
async def handle_user_choice(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()

    user_id = context.user_data.get("user_id")
    order_number = user_orders.get(user_id)

    if user_input == "continue":
        # Logic for continuing the shopping process
        await update.message.reply_text("Continuing your shopping... 🎉\nChoose what you'd like to buy next.")
        # You can redirect the user to the product list or shopping menu
        return ConversationHandler.END  # End the conversation or transition to the next state

    elif user_input == "track":
        # Logic to track the user's order
        if order_number:
            await update.message.reply_text(f"Your order number is: {order_number}. Tracking details will be sent soon.")
            # You can add further logic for tracking the order status
        else:
            await update.message.reply_text("Sorry, we couldn't find your order. Please try again later.")
        return ConversationHandler.END  # End the conversation

    elif user_input == "exit":
        # Exit the conversation and thank the user
        await update.message.reply_text("Thank you for using our service. Goodbye! 👋")
        return ConversationHandler.END  # End the conversation

    else:
        # Handle invalid input
        await update.message.reply_text("Invalid input. Please type 'continue', 'track', or 'exit'.")
        return NEXT_STEP  # Stay in the same state until a valid input is received

async def validate_payment(update: Update, context: CallbackContext):
    # Simulated validation (replace with actual logic)
    return True

async def cancel_payment(update: Update, context: CallbackContext):
    await update.message.reply_text("Payment process canceled. Returning to the main menu.", reply_markup=get_main_menu())
    return ConversationHandler.END

# Add handlers
payment_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now)],
    states={
        AFFILIATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_AFFILIATE_code)],
        AFFILIATE_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_AFFILIATE_code)],
        PAYMENT_METHOD: [CallbackQueryHandler(handle_payment, pattern="pay_.*")],  # Correct pattern
        PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_choice)]
    },
    fallbacks=[CommandHandler("cancel", cancel_payment)],
)

# Admin Commands
async def add_product(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    await update.message.reply_text("Please enter the product details in the format: <Category ID>|<Product Name>|<Price>")
    return ADD_PRODUCT

async def handle_add_product(update: Update, context):
    try:
        category_id, product_name, price = update.message.text.split("|")
        price = float(price)
        if category_id in db_categories:
            db_categories[category_id]["products"][product_name] = price
            await update.message.reply_text(f"Product '{product_name}' added to category {db_categories[category_id]['name']}.")
        else:
            await update.message.reply_text("Invalid category ID.")
    except Exception as e:
        await update.message.reply_text(f"Error adding product: {e}")
    return ConversationHandler.END

async def remove_product(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    await update.message.reply_text("Please enter the product name to remove:")
    return REMOVE_PRODUCT

async def handle_remove_product(update: Update, context):
    product_name = update.message.text.strip()
    for category_id, category in db_categories.items():
        if product_name in category["products"]:
            del category["products"][product_name]
            await update.message.reply_text(f"Product '{product_name}' removed from category {category['name']}.")
            return ConversationHandler.END
    await update.message.reply_text(f"Product '{product_name}' not found.")
    return ConversationHandler.END

async def generate_AFFILIATE_code(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    await update.message.reply_text("Please enter the expiry period for the AFFILIATE code (in days):")
    return GENERATE_CODE

async def handle_generate_AFFILIATE_code(update: Update, context):
    try:
        expiry_days = int(update.message.text.strip())
        expiry_date = datetime.now() + timedelta(days=expiry_days)
        code = str(uuid.uuid4())[:8]
        AFFILIATE_codes[code] = {"expiry": expiry_date, "AFFILIATE": 0.1}
        await update.message.reply_text(f"AFFILIATE code generated: {code}\nExpiry: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        await update.message.reply_text(f"Error generating AFFILIATE code: {e}")
    return ConversationHandler.END

async def check_AFFILIATE_code(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    await update.message.reply_text("Please enter the AFFILIATE code to check:")
    return AFFILIATE_CODE

async def handle_check_AFFILIATE_code(update: Update, context):
    code = update.message.text.strip()
    if code in AFFILIATE_codes:
        expiry = AFFILIATE_codes[code]["expiry"]
        if datetime.now() < expiry:
            await update.message.reply_text(f"AFFILIATE code '{code}' is valid until {expiry.strftime('%Y-%m-%d %H:%M:%S')}.")
        else:
            await update.message.reply_text(f"AFFILIATE code '{code}' has expired.")
    else:
        await update.message.reply_text(f"AFFILIATE code '{code}' not found.")
    return ConversationHandler.END

async def view_AFFILIATE_codes(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not AFFILIATE_codes:
        await update.message.reply_text("No AFFILIATE codes found.")
        return
    codes_text = "\n".join([f"Code: {code}, Expiry: {data['expiry'].strftime('%Y-%m-%d %H:%M:%S')}" for code, data in AFFILIATE_codes.items()])
    await update.message.reply_text(f"AFFILIATE Codes:\n{codes_text}")

async def view_user_orders(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not user_orders:
        await update.message.reply_text("No orders found.")
        return
    orders_text = "\n".join([f"User ID: {user_id}, Order Number: {order_number}" for user_id, order_number in user_orders.items()])
    await update.message.reply_text(f"User Orders:\n{orders_text}")

async def view_user_carts(update: Update, context):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not user_cart:
        await update.message.reply_text("No carts found.")
        return
    carts_text = "\n".join([f"User ID: {user_id}, Cart: {cart}" for user_id, cart in user_cart.items()])
    await update.message.reply_text(f"User Carts:\n{carts_text}")



# Missing Functions
async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())

async def back_to_categories(update: Update, context):
    query = update.callback_query
    await query.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def about(update: Update, context):
    await update.message.reply_text("This is a sample Telegram bot for an online store.")

async def support(update: Update, context):
    await update.message.reply_text("Contact support at support@example.com.")

# Conversation handler for admin commands
admin_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("addproduct", add_product),
        CommandHandler("removeproduct", remove_product),
        CommandHandler("generatecode", generate_AFFILIATE_code),
        CommandHandler("checkcode", check_AFFILIATE_code),
    ],
    states={
        ADD_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_product)],
        REMOVE_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_product)],
        GENERATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_AFFILIATE_code)],
        AFFILIATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_AFFILIATE_code)],
    },
    fallbacks=[]
)

application = Application.builder().token(TOKEN).build()

# Admin Conversation Handler (MUST COME BEFORE OTHER HANDLERS)
application.add_handler(admin_conv_handler)

# Other Handlers
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶ Start$"), handle_start_button))

application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Skip"), skip_AFFILIATE))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(CallbackQueryHandler(category_selected, pattern="category_.*"))
application.add_handler(CallbackQueryHandler(product_selected, pattern="product_.*"))
application.add_handler(CallbackQueryHandler(product_navigation, pattern="(next|back)_.*"))
application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
application.add_handler(CallbackQueryHandler(back_to_categories, pattern="back_to_categories"))

# Payment Conversation Handler (MUST COME AFTER ADMIN COMMANDS)
application.add_handler(payment_conv_handler)
application.add_handler(shipping_conversation)

# Cart Removal Handler (MUST COME AFTER ADMIN COMMANDS)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$") & ~filters.COMMAND, remove_from_cart))

# Start the bot
if __name__ == "__main__":
    application.run_polling()