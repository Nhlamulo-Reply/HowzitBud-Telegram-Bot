from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import db_categories

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🛍 Menu"), KeyboardButton("🛒 View Cart")],
            [KeyboardButton("💳 Pay Now"), KeyboardButton("Track Order")],
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

    buttons = []

    for idx, (product, price) in enumerate(current_products):
        product_idx = idx + (current_chunk * chunk_size)
        buttons.append([
            InlineKeyboardButton(f"🛒 Add {product} - R{price}", callback_data=f"add_{category_id}_{product_idx}"),
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