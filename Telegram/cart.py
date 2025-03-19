from telegram import Update
from telegram.ext import CallbackContext
from config import user_cart, DELIVERY_FEE
from keyboards import get_main_menu

async def view_cart(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    cart_items = user_cart.get(user_id, [])

    if not cart_items:
        await update.message.reply_text("🛒 Your cart is empty.", reply_markup=get_main_menu())
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

async def remove_from_cart(update: Update, context: CallbackContext):
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
