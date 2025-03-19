from telegram.ext import Application
from config import TOKEN
from Telegram.handlers import *
from Telegram.conversations import shipping_conversation, payment_conv_handler, quantity_conv_handler,skip_AFFILIATE
import paypalrestsdk
from Telegram.config import PAYPAL_CONFIG

# Initialize PayPal SDK
paypalrestsdk.configure(PAYPAL_CONFIG)

application = Application.builder().token(TOKEN).build()



from Telegram.admin import (
    admin_add_product_conv,
    admin_remove_product_conv,
    admin_generate_code_conv,
    admin_check_code_conv,
    view_affiliate_codes,
    view_user_orders,
    view_user_carts
)

# Add admin handlers to the application
application.add_handler(admin_add_product_conv)
application.add_handler(admin_remove_product_conv)
application.add_handler(admin_generate_code_conv)
application.add_handler(admin_check_code_conv)
application.add_handler(CommandHandler("view_codes", view_affiliate_codes))
application.add_handler(CommandHandler("view_orders", view_user_orders))
application.add_handler(CommandHandler("view_carts", view_user_carts))


# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶ Start$"), handle_start_button))
application.add_handler(payment_conv_handler)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛍 Menu"), show_menu))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("Skip"), skip_AFFILIATE))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("🛒 View Cart"), view_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("ℹ About"), about))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("❓ Help"), help))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("📞 Support"), support))
application.add_handler(CallbackQueryHandler(category_selected, pattern="category_.*"))
application.add_handler(CallbackQueryHandler(product_selected, pattern="add_.*"))
application.add_handler(CallbackQueryHandler(product_navigation, pattern="(next|back)_.*"))
application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
application.add_handler(CallbackQueryHandler(back_to_categories, pattern="back_to_categories"))
application.add_handler(shipping_conversation)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$") & ~filters.COMMAND, remove_from_cart))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+\s+\d+$") & ~filters.COMMAND, update_quantity))
application.add_handler(CallbackQueryHandler(set_quantity, pattern=r"^set_quantity_\d+_\d+$"))
application.add_handler(quantity_conv_handler)

logger.info("bot started")

# Start the bot
if __name__ == "__main__":
    application.run_polling()

    logger.info("bot closed")