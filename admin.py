# from datetime import datetime, timedelta
# import logging
# from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
# from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
# import paypalrestsdk
# import uuid
# # Product storage (you can use a database or in-memory storage for simplicity)
# PRODUCTS = {}
#
# # Add Product command handler
# async def add_product(update: Update, context: CallbackContext):
#     user_id = update.message.from_user.id
#     if user_id not in ADMINS:
#         await update.message.reply_text("❌ You are not authorized to add products.")
#         return
#
#     # Ask for product details
#     await update.message.reply_text("📦 Please send the product name.")
#     return ADD_PRODUCT_NAME
#
# # Handle the product name input
# async def handle_product_name(update: Update, context: CallbackContext):
#     context.user_data["product_name"] = update.message.text
#     await update.message.reply_text("📝 Please send the product description.")
#     return ADD_PRODUCT_DESCRIPTION
#
# # Handle product description
# async def handle_product_description(update: Update, context: CallbackContext):
#     context.user_data["product_description"] = update.message.text
#     await update.message.reply_text("💰 Please send the product price.")
#     return ADD_PRODUCT_PRICE
#
# # Handle product price
# async def handle_product_price(update: Update, context: CallbackContext):
#     try:
#         price = float(update.message.text)
#         context.user_data["product_price"] = price
#         await update.message.reply_text("🔗 Please send the product image URL.")
#         return ADD_PRODUCT_IMAGE
#     except ValueError:
#         await update.message.reply_text("❌ Please send a valid price.")
#
# # Handle product image URL
# async def handle_product_image(update: Update, context: CallbackContext):
#     image_url = update.message.text
#     context.user_data["product_image"] = image_url
#
#     # Store product details
#     product_name = context.user_data["product_name"]
#     PRODUCTS[product_name] = {
#         "name": product_name,
#         "description": context.user_data["product_description"],
#         "price": context.user_data["product_price"],
#         "image_url": image_url,
#     }
#
#     await update.message.reply_text(f"✅ Product '{product_name}' added successfully!")
#     return ConversationHandler.END
#
# # Set conversation handler for adding products
# add_product_conv_handler = ConversationHandler(
#     entry_points=[CommandHandler("add_product", add_product)],
#     states={
#         ADD_PRODUCT_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_product_name)],
#         ADD_PRODUCT_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, handle_product_description)],
#         ADD_PRODUCT_PRICE: [MessageHandler(Filters.text & ~Filters.command, handle_product_price)],
#         ADD_PRODUCT_IMAGE: [MessageHandler(Filters.text & ~Filters.command, handle_product_image)],
#     },
#     fallbacks=[],
# )
#
# # Remove Product command handler
# async def remove_product(update: Update, context: CallbackContext):
#     user_id = update.message.from_user.id
#     if user_id not in ADMINS:
#         await update.message.reply_text("❌ You are not authorized to remove products.")
#         return
#
#     product_name = update.message.text.strip()
#     if product_name in PRODUCTS:
#         del PRODUCTS[product_name]
#         await update.message.reply_text(f"✅ Product '{product_name}' removed successfully!")
#     else:
#         await update.message.reply_text(f"❌ Product '{product_name}' not found.")
#
# # Add remove product command
# application.add_handler(CommandHandler("remove_product", remove_product))
#
# import random
# import string
#
# # Affiliate codes storage (this could also be in a database)
# AFFILIATE_CODES = {}
#
# # Generate affiliate code
# def generate_affiliate_code():
#     return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
#
# # Command to generate affiliate code
# async def generate_affiliate(update: Update, context: CallbackContext):
#     user_id = update.message.from_user.id
#     if user_id not in ADMINS:
#         await update.message.reply_text("❌ You are not authorized to generate affiliate codes.")
#         return
#
#     # Ask for the expiration period (in days)
#     await update.message.reply_text("⏳ Please send the expiration period in days.")
#     return AFFILIATE_EXPIRATION
#
# # Handle expiration period input
# async def handle_affiliate_expiration(update: Update, context: CallbackContext):
#     try:
#         days = int(update.message.text)
#         expiration_date = datetime.now() + timedelta(days=days)
#         affiliate_code = generate_affiliate_code()
#
#         # Store the affiliate code and its expiration date
#         AFFILIATE_CODES[affiliate_code] = {
#             "expiration_date": expiration_date,
#             "user_id": update.message.from_user.id,
#         }
#
#         await update.message.reply_text(f"✅ Affiliate code '{affiliate_code}' generated! It will expire on {expiration_date}.")
#         return ConversationHandler.END
#     except ValueError:
#         await update.message.reply_text("❌ Please send a valid number of days.")
#
# # Add affiliate generation handler
# generate_affiliate_conv_handler = ConversationHandler(
#     entry_points=[CommandHandler("generate_affiliate", generate_affiliate)],
#     states={AFFILIATE_EXPIRATION: [MessageHandler(Filters.text & ~Filters.command, handle_affiliate_expiration)]},
#     fallbacks=[],
# )
#
# # Check Affiliate code expiration
# async def check_affiliate(update: Update, context: CallbackContext):
#     user_id = update.message.from_user.id
#     if user_id not in ADMINS:
#         await update.message.reply_text("❌ You are not authorized to check affiliate codes.")
#         return
#
#     affiliate_code = update.message.text.strip()
#     if affiliate_code in AFFILIATE_CODES:
#         affiliate_data = AFFILIATE_CODES[affiliate_code]
#         expiration_date = affiliate_data["expiration_date"]
#         if expiration_date > datetime.now():
#             await update.message.reply_text(f"✅ Affiliate code '{affiliate_code}' is valid until {expiration_date}.")
#         else:
#             await update.message.reply_text(f"❌ Affiliate code '{affiliate_code}' has expired.")
#     else:
#         await update.message.reply_text(f"❌ Affiliate code '{affiliate_code}' not found.")
#
# # Add check affiliate code command
# application.add_handler(CommandHandler("check_affiliate", check_affiliate))
