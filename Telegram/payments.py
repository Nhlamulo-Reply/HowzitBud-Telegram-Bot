from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, \
    CommandHandler
from config import user_cart, user_orders, user_AFFILIATE_codes, DELIVERY_FEE, ADMIN_USER_ID, cancel_payment
import paypalrestsdk
import uuid
from keyboards import get_main_menu
from datetime import datetime

# Payment states
PAYMENT_CONFIRMATION, NEXT_STEP = range(2)

async def pay_now(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
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

async def handle_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = context.user_data["user_id"]
    cart_items = user_cart.get(user_id, [])
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items) + DELIVERY_FEE

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

    if user_input == "payment completed":
        order_number = str(uuid.uuid4())[:8]
        user_orders[user_id] = order_number
        await update.message.reply_text(f"✅ Payment confirmed! Your order number is: {order_number}")

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
        await update.message.reply_text("⚠ Payment not confirmed. Please type 'Payment Completed' once payment is done.")
        return PAYMENT_CONFIRMATION

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

payment_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("💳 Pay Now"), pay_now)],
    states={
        PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel_payment)],
)