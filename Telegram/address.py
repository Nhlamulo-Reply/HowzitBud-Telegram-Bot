from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, filters, CommandHandler

from Telegram.conversations import DISCOUNT_CODE
from config import user_orders
from Telegram.keyboards import *

# Address states
FULL_NAME, PHONE, ADDRESS, CITY, COUNTRY, CONFIRM = range(6)

async def start_shipping(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter your full name:")
    return FULL_NAME
async def full_name(update: Update, context: CallbackContext):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text("Enter your phone number:")
    return PHONE
async def phone(update: Update, context: CallbackContext):
    context.user_data["phone"] = update.message.text
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
    context.user_data["province"] = update.message.text
    user_info = f"""
📦 **Shipping Address:**
👤 Name: {context.user_data['full_name']}
📞 Phone: {context.user_data['phone'] or 'Not provided'}
🏠 Address: {context.user_data['address']}
🌍 City: {context.user_data['city']}
🌎 Province: {context.user_data['country']}

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


        await update.message.reply_text("✅ Your shipping details have been saved!\n\n💳 Now you can proceed to payment.",reply_markup=get_main_menu())
        await update.message.reply_text("Do you have a discount code? (Type 'yes' to enter a code or 'no' to skip):")
        return DISCOUNT_CODE

    else:
        await update.message.reply_text("❌ Shipping details discarded. Start again with /shipping.",reply_markup=get_main_menu())
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
    },
    fallbacks=[],
)