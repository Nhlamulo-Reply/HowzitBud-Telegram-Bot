from telegram import Update
from telegram.ext import CallbackContext
from config import db_categories, user_cart
from keyboards import get_product_buttons

async def show_menu(update: Update, context: CallbackContext):
    await update.message.reply_text("Select a category:", reply_markup=get_category_buttons())

async def category_selected(update: Update, context: CallbackContext):
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