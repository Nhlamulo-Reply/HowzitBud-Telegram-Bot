# Add to global variables
import buttons
from telegram import InlineKeyboardButton, Update
from telegram.ext import CallbackContext, CallbackQueryHandler


from bot import *

user_wishlist = {}

# Add to get_product_buttons function
buttons.append([
    InlineKeyboardButton("❤️ Add to Wishlist", callback_data=f"wishlist_{category_id}_{product_idx}")
])

# Add wishlist handlers
async def add_to_wishlist(update: Update, context: CallbackContext):
    query = update.callback_query
    _, category_id, product_idx = query.data.split("_")
    product_idx = int(product_idx)

    category = db_categories.get(category_id, {})
    products = list(category.get("products", {}).items())

    if 0 <= product_idx < len(products):
        product_name, price = products[product_idx]
        user_id = query.from_user.id

        if user_id not in user_wishlist:
            user_wishlist[user_id] = []

        if product_name not in [item["name"] for item in user_wishlist[user_id]]:
            user_wishlist[user_id].append({"name": product_name, "price": price})
            await query.answer(f"✅ Added {product_name} to wishlist!")
        else:
            await query.answer(f"❌ {product_name} is already in your wishlist.")
    else:
        await query.answer("❌ Invalid product selection.")

async def view_wishlist(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    wishlist_items = user_wishlist.get(user_id, [])

    if not wishlist_items:
        await update.message.reply_text("❤️ Your wishlist is empty.", reply_markup=get_main_menu())
        return

    wishlist_text = "❤️ *Your Wishlist:*\n"
    for idx, item in enumerate(wishlist_items, start=1):
        wishlist_text += f"{idx}. {item['name']} - R{item['price']}\n"

    await update.message.reply_text(wishlist_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Add to Cart", callback_data="add_from_wishlist")],
        [InlineKeyboardButton("🗑️ Remove Item", callback_data="remove_from_wishlist")]
    ]))

# Add handlers to the application
application.add_handler(CallbackQueryHandler(add_to_wishlist, pattern="^wishlist_.*"))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^❤️ Wishlist$"), view_wishlist))