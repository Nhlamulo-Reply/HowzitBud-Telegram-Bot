from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from keyboards import get_main_menu, get_category_buttons, get_product_buttons
from config import db_categories, DELIVERY_FEE
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Conversation states
FULL_NAME, PHONE, ADDRESS, CITY, COUNTRY, CONFIRM, DISCOUNT_CODE, PAYMENT_CONFIRMATION, NEXT_STEP = range(9)
AFFILIATE_CODE, AFFILIATE_CODE_INPUT, PAYMENT_METHOD, ADD_PRODUCT, REMOVE_PRODUCT, GENERATE_CODE = range(6)

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

    await show_payment_methods(update, context)
    return PAYMENT_METHOD

async def handle_payment(update: Update, context):
    query = update.callback_query
    user_id = context.user_data["user_id"]
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] for item in cart_items) + DELIVERY_FEE

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
        bitcoin_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        await query.message.reply_text(f"Please send R{total_amount:.2f} to the following Bitcoin address: {bitcoin_address}")
    elif query.data == "pay_fnb":
        await query.message.reply_text("Please use the following FNB account details for payment:\n\n"
                                       "Bank: FNB\n"
                                       "Account Number: 63086573681\n"
                                       "Branch Code: 250655\n"
                                       "Reference: Your Order Number")
    elif query.data == "back_to_menu":
        await query.message.reply_text("Returning to main menu.", reply_markup=get_main_menu())

    order_number = str(uuid.uuid4())[:8]
    user_orders[user_id] = order_number
    await query.message.reply_text(f"Your order number is: {order_number}")

    await query.message.reply_text("Once done, type 'Payment Completed' to confirm.")
    context.user_data["awaiting_payment_confirmation"] = True
    return PAYMENT_CONFIRMATION

async def payment_confirmation(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()

    user_id = context.user_data.get("user_id")
    if not user_id:
        await update.message.reply_text("⚠ Error: User ID not found. Please restart the payment process.")
        return ConversationHandler.END

    if user_input == "payment completed":
        is_valid = await validate_payment(update, context)

        if is_valid:
            order_number = str(uuid.uuid4())[:8]
            user_orders[user_id] = order_number

            await update.message.reply_text(f"✅ Payment confirmed!")

            admin_message = f"🛒 New Order:\n👤 User ID: {user_id}\n📦 Order Number: {order_number}"
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

            await update.message.reply_text(
                "What would you like to do next?\n"
                "1. Type 'continue' to continue shopping.\n"
                "2. Type 'track' to track your order.\n"
                "3. Type 'exit' to end the conversation."
            )

            return NEXT_STEP

        else:
            await update.message.reply_text("❌ Payment validation failed. Please try again.")
            return PAYMENT_CONFIRMATION

    else:
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

quantity_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_quantity, pattern=r"^set_quantity_\d+_\d+$")],
    states={
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_quantity)]
    },
    fallbacks=[],
)