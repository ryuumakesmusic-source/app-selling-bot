import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MENU_TITLE = "Welcome to the store. Choose an option:"
REGISTERED_USERS: set[int] = set()
PURCHASES: dict[int, list[str]] = {}
PRODUCTS: list[dict[str, str]] = []


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🛍️ Products", callback_data="menu:products"),
                InlineKeyboardButton("👤 Profile", callback_data="menu:profile"),
            ],
            [
                InlineKeyboardButton("👥 Referrals", callback_data="menu:referrals"),
                InlineKeyboardButton("🛠️ Support", callback_data="menu:support"),
            ],
            [InlineKeyboardButton("🔐 Admin", callback_data="menu:admin")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩️ Back to menu", callback_data="menu:back")]]
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🧾 Check purchase history", callback_data="menu:history"
                )
            ],
            [InlineKeyboardButton("↩️ Back to menu", callback_data="menu:back")],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add item", callback_data="menu:add_item")],
            [
                InlineKeyboardButton(
                    "📦 Add accounts", callback_data="menu:add_accounts"
                )
            ],
            [InlineKeyboardButton("↩️ Back to menu", callback_data="menu:back")],
        ]
    )


def add_accounts_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index, product in enumerate(PRODUCTS):
        rows.append(
            [
                InlineKeyboardButton(
                    product["name"],
                    callback_data=f"menu:add_accounts:{index}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("↩️ Back to menu", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def products_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index, product in enumerate(PRODUCTS):
        label = f"{product['name']} - {product['price']} MMK"
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"menu:product:{index}")]
        )
    rows.append([InlineKeyboardButton("↩️ Back to menu", callback_data="menu:back")])
    return InlineKeyboardMarkup(rows)


def dashboard_lines(user: object) -> list[str]:
    if hasattr(user, "id"):
        user_id = user.id
    else:
        user_id = "-"
    if hasattr(user, "first_name") and user.first_name:
        first_name = user.first_name
    else:
        first_name = "-"
    return [
        "👋 Welcome to the RYUU store!",
        "",
        f"🆔 ID: {user_id}",
        f"👤 Name: {first_name}",
        f"👥 Users: {len(REGISTERED_USERS)}",
        "",
        f"🏠 {MENU_TITLE}",
    ]


def profile_lines(user: object) -> list[str]:
    if hasattr(user, "id"):
        user_id = user.id
    else:
        user_id = "-"
    if hasattr(user, "first_name") and user.first_name:
        first_name = user.first_name
    else:
        first_name = "-"

    purchase_count = len(PURCHASES.get(user_id, [])) if isinstance(user_id, int) else 0
    return [
        f"🆔 ID: {user_id}",
        f"👤 Name: {first_name}",
        f"🧾 Purchases: {purchase_count}",
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        user = update.effective_user
        user_id = user.id if user else "-"
        if isinstance(user_id, int):
            REGISTERED_USERS.add(user_id)
        await update.message.reply_text(
            "\n".join(dashboard_lines(user)), reply_markup=menu_keyboard()
        )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    action = query.data or ""

    if action == "menu:back":
        await query.edit_message_text(
            "\n".join(dashboard_lines(query.from_user)),
            reply_markup=menu_keyboard(),
        )
        return

    if action == "menu:profile":
        await query.edit_message_text(
            "\n".join(profile_lines(query.from_user)),
            reply_markup=profile_keyboard(),
        )
        return

    if action == "menu:admin":
        await query.edit_message_text(
            "🔐 Admin panel:",
            reply_markup=admin_keyboard(),
        )
        return

    if action == "menu:add_item":
        context.user_data["awaiting"] = "product_name"
        if query.message:
            context.user_data["admin_chat_id"] = query.message.chat_id
            context.user_data["admin_message_id"] = query.message.message_id
        await query.edit_message_text(
            "➕ Send the product name:", reply_markup=admin_keyboard()
        )
        return

    if action == "menu:add_accounts":
        if not PRODUCTS:
            await query.edit_message_text(
                "📦 No products yet. Add a product first.",
                reply_markup=admin_keyboard(),
            )
            return
        await query.edit_message_text(
            "📦 Choose a product to add accounts:",
            reply_markup=add_accounts_keyboard(),
        )
        return

    if action.startswith("menu:add_accounts:"):
        index_str = action.split(":", 2)[2]
        if not index_str.isdigit():
            await query.edit_message_text(
                "📦 Invalid selection.", reply_markup=admin_keyboard()
            )
            return
        index = int(index_str)
        if index < 0 or index >= len(PRODUCTS):
            await query.edit_message_text(
                "📦 Product not found.", reply_markup=admin_keyboard()
            )
            return
        product = PRODUCTS[index]["name"]
        await query.edit_message_text(
            f"📦 Add accounts for {product} (coming soon).",
            reply_markup=admin_keyboard(),
        )
        return

    if action.startswith("menu:product:"):
        index_str = action.split(":", 2)[2]
        if not index_str.isdigit():
            await query.edit_message_text(
                "🛍️ Invalid selection.", reply_markup=back_keyboard()
            )
            return
        index = int(index_str)
        if index < 0 or index >= len(PRODUCTS):
            await query.edit_message_text(
                "🛍️ Product not found.", reply_markup=back_keyboard()
            )
            return
        product = PRODUCTS[index]
        await query.edit_message_text(
            f"🛍️ {product['name']} - {product['price']} MMK\n\n"
            "Buying flow coming soon.",
            reply_markup=back_keyboard(),
        )
        return

    if action == "menu:history":
        items = PURCHASES.get(query.from_user.id, [])
        if items:
            lines = ["🧾 Purchase history:"]
            lines.extend(f"- {item}" for item in items)
            message = "\n".join(lines)
        else:
            message = "🧾 No purchases yet."
        await query.edit_message_text(message, reply_markup=profile_keyboard())
        return

    if action == "menu:products":
        if not PRODUCTS:
            message = "🛍️ No products yet."
            await query.edit_message_text(message, reply_markup=back_keyboard())
            return
        await query.edit_message_text(
            "🛍️ Choose a product:", reply_markup=products_keyboard()
        )
        return

    messages = {
        "menu:referrals": "👥 Referral info will be available here soon.",
        "menu:support": "🛠️ Support options will be available here soon.",
    }
    message = messages.get(action, "Unknown option.")
    await query.edit_message_text(message, reply_markup=back_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()
    if not text:
        return

    if awaiting == "product_name":
        await delete_message_safe(context, update.message.chat_id, update.message.id)
        context.user_data["new_product_name"] = text
        context.user_data["awaiting"] = "product_price"
        if not await edit_admin_message_safe(
            context,
            "💵 Send the product price:",
            reply_markup=admin_keyboard(),
        ):
            await update.message.reply_text("💵 Send the product price:")
        return

    if awaiting == "product_price":
        await delete_message_safe(context, update.message.chat_id, update.message.id)
        product_name = context.user_data.get("new_product_name")
        if not product_name:
            context.user_data.pop("awaiting", None)
            if not await edit_admin_message_safe(
                context,
                "⚠️ Missing product name. Try again.",
                reply_markup=admin_keyboard(),
            ):
                await update.message.reply_text("⚠️ Missing product name. Try again.")
            return
        PRODUCTS.append({"name": product_name, "price": text})
        context.user_data.pop("awaiting", None)
        context.user_data.pop("new_product_name", None)
        if not await edit_admin_message_safe(
            context,
            f"✅ Added product: {product_name} — {text}",
            reply_markup=admin_keyboard(),
        ):
            await update.message.reply_text(
                f"✅ Added product: {product_name} — {text}",
                reply_markup=admin_keyboard(),
            )
        return


def load_token_from_env_file() -> str | None:
    try:
        with open(".env", "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith("BOT_TOKEN="):
                    continue
                value = line.split("=", 1)[1].strip()
                if value.startswith("\"") and value.endswith("\""):
                    value = value[1:-1]
                return value or None
    except FileNotFoundError:
        return None
    return None


async def delete_message_safe(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int
) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        return


async def edit_admin_message_safe(
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    chat_id = context.user_data.get("admin_chat_id")
    message_id = context.user_data.get("admin_message_id")
    if not chat_id or not message_id:
        return False
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except TelegramError:
        return False


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        token = load_token_from_env_file()
    if not token:
        raise SystemExit("BOT_TOKEN is not set.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu, pattern="^menu:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
