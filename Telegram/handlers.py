from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from keyboards import get_main_menu, get_category_buttons, get_product_buttons
from config import db_categories, DELIVERY_FEE
import logging

logger = logging.getLogger(__name__)

# User Cart Storage
user_cart = {}
user_position = {}
user_orders = {}
user_AFFILIATE_codes = {}
first_time_users = {}

# AFFILIATE Codes Storage
AFFILIATE_codes = {}  # Format: {"code": {"expiry": datetime, "AFFILIATE": 0.1}}

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

    if first_time_users.get(user_id, False):
        first_time_users[user_id] = False
        await update.message.reply_text(
            "Welcome to our store! Here's how you can navigate:\n"
            "1. Browse through our menu to view products.\n"
            "2. Add items to your cart and proceed to checkout.\n"
            "3. Pay via your preferred method (PayPal, PayFast, or Bitcoin).\n"
            "Click 'Menu' to start shopping.",
            reply_markup=get_main_menu()
        )
    else:
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

        user_cart[user_id].append({"name": product_name, "price": price, "quantity": 1})

        await query.answer(f"✅ Added 1x {product_name} to cart!")

        new_reply_markup = get_product_buttons(category_id, product_idx)

        if new_reply_markup != query.message.reply_markup:
            await query.message.edit_reply_markup(reply_markup=new_reply_markup)
    else:
        await query.answer("❌ Invalid product selection.")

async def view_cart(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await update.message.reply_text("🛒 Your cart is empty." , reply_markup=get_main_menu() )
        return

    cart_details = "\n".join([
        f"{idx + 1}. {item['quantity']}x {item['name']} - R{item['price'] * item['quantity']}"
        for idx, item in enumerate(cart_items)
    ])

    total_amount = sum(item['price'] * item['quantity'] for item in cart_items) + DELIVERY_FEE

    await update.message.reply_text(
        f"🛒 Your Cart:\n{cart_details}\n\n🚚 Delivery Fee: R{DELIVERY_FEE}\n"
        f"💰 Total: R{total_amount}\n\nReply with the item number to remove or edit quantity.",
        reply_markup=get_main_menu()
    )

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

async def support(update: Update, context: CallbackContext):
    await update.message.reply_text("Contact support at support@example.com.")

async def back_to_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Returning to the main menu.", reply_markup=get_main_menu())