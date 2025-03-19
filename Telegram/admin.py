from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, filters, CommandHandler
from datetime import datetime, timedelta
import uuid
from config import ADMIN_USER_ID, db_categories, affiliate_codes, user_orders, user_cart

# Conversation states for admin commands
ADD_PRODUCT, REMOVE_PRODUCT, GENERATE_CODE, AFFILIATE_CODE = range(4)

# Admin command: Add a product
async def add_product(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END
    await update.message.reply_text("Please enter the product details in the format: <Category ID>|<Product Name>|<Price>")
    return ADD_PRODUCT

async def handle_add_product(update: Update, context: CallbackContext):
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

# Admin command: Remove a product
async def remove_product(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END
    await update.message.reply_text("Please enter the product name to remove:")
    return REMOVE_PRODUCT

async def handle_remove_product(update: Update, context: CallbackContext):
    product_name = update.message.text.strip()
    for category_id, category in db_categories.items():
        if product_name in category["products"]:
            del category["products"][product_name]
            await update.message.reply_text(f"Product '{product_name}' removed from category {category['name']}.")
            return ConversationHandler.END
    await update.message.reply_text(f"Product '{product_name}' not found.")
    return ConversationHandler.END

# Admin command: Generate an affiliate code
async def generate_affiliate_code(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END
    await update.message.reply_text("Please enter the expiry period for the affiliate code (in days):")
    return GENERATE_CODE

async def handle_generate_affiliate_code(update: Update, context: CallbackContext):
    try:
        expiry_days = int(update.message.text.strip())
        expiry_date = datetime.now() + timedelta(days=expiry_days)
        code = str(uuid.uuid4())[:8]
        affiliate_codes[code] = {"expiry": expiry_date, "discount": 0.1}
        await update.message.reply_text(f"Affiliate code generated: {code}\nExpiry: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        await update.message.reply_text(f"Error generating affiliate code: {e}")
    return ConversationHandler.END

# Admin command: Check an affiliate code
async def check_affiliate_code(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return ConversationHandler.END
    await update.message.reply_text("Please enter the affiliate code to check:")
    return AFFILIATE_CODE

async def handle_check_affiliate_code(update: Update, context: CallbackContext):
    code = update.message.text.strip()
    if code in affiliate_codes:
        expiry = affiliate_codes[code]["expiry"]
        if datetime.now() < expiry:
            await update.message.reply_text(f"Affiliate code '{code}' is valid until {expiry.strftime('%Y-%m-%d %H:%M:%S')}.")
        else:
            await update.message.reply_text(f"Affiliate code '{code}' has expired.")
    else:
        await update.message.reply_text(f"Affiliate code '{code}' not found.")
    return ConversationHandler.END

# Admin command: View all affiliate codes
async def view_affiliate_codes(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not affiliate_codes:
        await update.message.reply_text("No affiliate codes found.")
        return
    codes_text = "\n".join([f"Code: {code}, Expiry: {data['expiry'].strftime('%Y-%m-%d %H:%M:%S')}" for code, data in affiliate_codes.items()])
    await update.message.reply_text(f"Affiliate Codes:\n{codes_text}")

# Admin command: View all user orders
async def view_user_orders(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not user_orders:
        await update.message.reply_text("No orders found.")
        return
    orders_text = "\n".join([f"User ID: {user_id}, Order Number: {order_number}" for user_id, order_number in user_orders.items()])
    await update.message.reply_text(f"User Orders:\n{orders_text}")

# Admin command: View all user carts
async def view_user_carts(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to perform this action.")
        return
    if not user_cart:
        await update.message.reply_text("No carts found.")
        return
    carts_text = "\n".join([f"User ID: {user_id}, Cart: {cart}" for user_id, cart in user_cart.items()])
    await update.message.reply_text(f"User Carts:\n{carts_text}")

# Admin conversation handlers
admin_add_product_conv = ConversationHandler(
    entry_points=[CommandHandler("add_product", add_product)],
    states={
        ADD_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_product)],
    },
    fallbacks=[],
)

admin_remove_product_conv = ConversationHandler(
    entry_points=[CommandHandler("remove_product", remove_product)],
    states={
        REMOVE_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_product)],
    },
    fallbacks=[],
)

admin_generate_code_conv = ConversationHandler(
    entry_points=[CommandHandler("generate_code", generate_affiliate_code)],
    states={
        GENERATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_affiliate_code)],
    },
    fallbacks=[],
)

admin_check_code_conv = ConversationHandler(
    entry_points=[CommandHandler("check_code", check_affiliate_code)],
    states={
        AFFILIATE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_affiliate_code)],
    },
    fallbacks=[],
)