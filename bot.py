import logging
import json
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from database import get_db
from config import (
    BOT_TOKEN, ADMIN_CHAT_ID, DELIVERY_OPTIONS, BASE_URL
)

PAYNOW_QR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paynow_qr.jpg")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REG_NAME, REG_PHONE, REG_COUNTRY = range(3)
CHECKOUT_NAME, CHECKOUT_PHONE, CHECKOUT_ADDRESS, CHECKOUT_DELIVERY = range(10, 14)
ENQUIRY_MSG = 20
SUPPORT_REPLY = 30


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    db = await get_db()
    cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = await cursor.fetchone()
    await db.close()

    if user:
        await show_main_menu(update, context)
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to Health & Wellness Store!\n\n"
        "Let's get you registered. What is your full name?"
    )
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text.strip()
    button = KeyboardButton("Share Phone Number", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Thanks! Please share your phone number:",
        reply_markup=markup
    )
    return REG_PHONE


async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    context.user_data["reg_phone"] = phone
    await update.message.reply_text("Which country are you from?")
    return REG_COUNTRY


async def reg_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.strip()
    telegram_id = update.effective_user.id
    username = update.effective_user.username or ""
    full_name = context.user_data.get("reg_name", "")
    phone = context.user_data.get("reg_phone", "")

    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, full_name, phone, country) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, username, full_name, phone, country)
    )
    await db.commit()
    await db.close()

    await update.message.reply_text(
        f"Registration complete! Welcome, {full_name}!\n\n"
        "You can now browse our products and place orders."
    )
    await show_main_menu(update, context)
    return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Browse Products", callback_data="browse")],
        [InlineKeyboardButton("My Cart", callback_data="cart"),
         InlineKeyboardButton("My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("FAQ", callback_data="faq"),
         InlineKeyboardButton("Contact Support", callback_data="support")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = (
        "Health & Wellness Store\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "What would you like to do?"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def browse_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = await get_db()
    cursor = await db.execute("SELECT id, name, description FROM categories ORDER BY sort_order")
    categories = await cursor.fetchall()
    await db.close()

    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(
            f"{cat[1]}", callback_data=f"cat_{cat[0]}"
        )])
    keyboard.append([InlineKeyboardButton("Back to Menu", callback_data="main_menu")])

    await query.edit_message_text(
        "Product Categories\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select a category to browse:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])

    db = await get_db()
    cursor = await db.execute(
        "SELECT p.id, p.name, p.price, c.name FROM products p "
        "JOIN categories c ON p.category_id = c.id "
        "WHERE p.category_id = ? AND p.in_stock = 1",
        (cat_id,)
    )
    products = await cursor.fetchall()
    await db.close()

    if not products:
        keyboard = [[InlineKeyboardButton("Back", callback_data="browse")]]
        await query.edit_message_text("No products available in this category.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    cat_name = products[0][3]
    keyboard = []
    for prod in products:
        keyboard.append([InlineKeyboardButton(
            f"{prod[1]} - SGD {prod[2]:.2f}", callback_data=f"prod_{prod[0]}"
        )])
    keyboard.append([InlineKeyboardButton("Back to Categories", callback_data="browse")])

    await query.edit_message_text(
        f"{cat_name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select a product for details:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[1])

    db = await get_db()
    cursor = await db.execute(
        "SELECT p.*, c.name as cat_name FROM products p "
        "JOIN categories c ON p.category_id = c.id WHERE p.id = ?",
        (prod_id,)
    )
    product = await cursor.fetchone()

    pkg_cursor = await db.execute(
        "SELECT id, name, price FROM package_options WHERE product_id = ?",
        (prod_id,)
    )
    packages = await pkg_cursor.fetchall()
    await db.close()

    if not product:
        return

    # columns: 0=id, 1=category_id, 2=name, 3=description, 4=benefits, 5=usage_info, 6=full_info, 7=price, 8=image_url, 9=in_stock, 10=created_at, 11=cat_name
    text = f"{product[2]}\n━━━━━━━━━━━━━━━━━━\n\n"

    if product[4]:
        text += "Benefits\n"
        for line in product[4].split("\n"):
            line = line.strip()
            if line:
                label = line.split(":", 1)[0].strip() if ":" in line else line
                text += f"  - {label}\n"
        text += "\n"

    if product[5]:
        text += "Usage\n"
        first_sentence = product[5].split(".")[0].strip()
        if first_sentence:
            text += f"  - {first_sentence}\n\n"

    if packages:
        text += "Packages\n"
        for pkg in packages:
            text += f"  - {pkg[1]} - SGD {pkg[2]:.2f}\n"
        text += "\n"

    keyboard = []
    if packages:
        for pkg in packages:
            keyboard.append([InlineKeyboardButton(
                f"Add: {pkg[1]} - SGD {pkg[2]:.2f}",
                callback_data=f"addpkg_{prod_id}_{pkg[0]}"
            )])
    else:
        keyboard.append([InlineKeyboardButton(
            f"Add to Cart - SGD {product[7]:.2f}",
            callback_data=f"add_{prod_id}"
        )])

    keyboard.append([InlineKeyboardButton("View Full Information", callback_data=f"fullinfo_{prod_id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data=f"cat_{product[1]}")])
    keyboard.append([InlineKeyboardButton("Main Menu", callback_data="main_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_product_full_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[1])

    db = await get_db()
    cursor = await db.execute(
        "SELECT p.*, c.name as cat_name FROM products p "
        "JOIN categories c ON p.category_id = c.id WHERE p.id = ?",
        (prod_id,)
    )
    product = await cursor.fetchone()
    await db.close()

    if not product:
        return

    # columns: 0=id, 1=category_id, 2=name, 3=description, 4=benefits, 5=usage_info, 6=full_info, 7=price, 8=image_url, 9=in_stock, 10=created_at, 11=cat_name
    header = f"{product[2]}\n━━━━━━━━━━━━━━━━━━\n\n"

    if product[6]:
        full_text = header + product[6]
    else:
        full_text = header
        if product[3]:
            full_text += f"Description\n{product[3]}\n\n"
        if product[4]:
            full_text += f"Benefits\n{product[4]}\n\n"
        if product[5]:
            full_text += f"Usage\n{product[5]}\n"

    keyboard = [
        [InlineKeyboardButton("Back to Product", callback_data=f"prod_{prod_id}")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if len(full_text) <= 4096:
        await query.edit_message_text(full_text, reply_markup=markup)
    else:
        await query.edit_message_text(full_text[:4096], reply_markup=None)
        remaining = full_text[4096:]
        chat_id = query.from_user.id
        while len(remaining) > 4096:
            await context.bot.send_message(chat_id=chat_id, text=remaining[:4096])
            remaining = remaining[4096:]
        await context.bot.send_message(chat_id=chat_id, text=remaining, reply_markup=markup)


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Added to cart!")
    data = query.data
    telegram_id = update.effective_user.id

    if data.startswith("addpkg_"):
        parts = data.split("_")
        prod_id = int(parts[1])
        pkg_id = int(parts[2])
    else:
        prod_id = int(data.split("_")[1])
        pkg_id = None

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO cart_items (telegram_id, product_id, package_option_id, quantity) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(telegram_id, product_id, package_option_id) "
            "DO UPDATE SET quantity = quantity + 1",
            (telegram_id, prod_id, pkg_id)
        )
        await db.commit()
    finally:
        await db.close()

    keyboard = [
        [InlineKeyboardButton("View Cart", callback_data="cart")],
        [InlineKeyboardButton("Continue Shopping", callback_data="browse")],
    ]
    await query.edit_message_text(
        "Item added to your cart!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    db = await get_db()
    cursor = await db.execute(
        "SELECT ci.id, p.name, ci.quantity, "
        "COALESCE(po.price, p.price) as price, "
        "COALESCE(po.name, '') as pkg_name "
        "FROM cart_items ci "
        "JOIN products p ON ci.product_id = p.id "
        "LEFT JOIN package_options po ON ci.package_option_id = po.id "
        "WHERE ci.telegram_id = ?",
        (telegram_id,)
    )
    items = await cursor.fetchall()
    await db.close()

    if not items:
        keyboard = [
            [InlineKeyboardButton("Browse Products", callback_data="browse")],
            [InlineKeyboardButton("Main Menu", callback_data="main_menu")],
        ]
        await query.edit_message_text(
            "Your cart is empty.\n\nBrowse our products to add items!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    text = "Your Shopping Cart\n━━━━━━━━━━━━━━━━━━\n\n"
    total = 0
    keyboard = []

    for item in items:
        item_total = item[3] * item[2]
        total += item_total
        pkg_info = f" ({item[4]})" if item[4] else ""
        text += f"{item[1]}{pkg_info}\n  Qty: {item[2]} x SGD {item[3]:.2f} = SGD {item_total:.2f}\n\n"
        keyboard.append([
            InlineKeyboardButton(f"- {item[1][:20]}", callback_data=f"cartdec_{item[0]}"),
            InlineKeyboardButton(f"+ {item[1][:20]}", callback_data=f"cartinc_{item[0]}"),
            InlineKeyboardButton("Remove", callback_data=f"cartdel_{item[0]}"),
        ])

    text += f"━━━━━━━━━━━━━━━━━━\nSubtotal: SGD {total:.2f}"
    context.user_data["cart_subtotal"] = total

    keyboard.append([InlineKeyboardButton("Proceed to Checkout", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("Continue Shopping", callback_data="browse")])
    keyboard.append([InlineKeyboardButton("Main Menu", callback_data="main_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def update_cart_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    action = data.split("_")[0]
    item_id = int(data.split("_")[1])

    db = await get_db()
    if action == "cartdel":
        await db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        await query.answer("Item removed")
    elif action == "cartinc":
        await db.execute("UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?", (item_id,))
        await query.answer("Quantity increased")
    elif action == "cartdec":
        cursor = await db.execute("SELECT quantity FROM cart_items WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        if row and row[0] > 1:
            await db.execute("UPDATE cart_items SET quantity = quantity - 1 WHERE id = ?", (item_id,))
            await query.answer("Quantity decreased")
        else:
            await db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
            await query.answer("Item removed")
    await db.commit()
    await db.close()

    update.callback_query = query
    await show_cart(update, context)


async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    db = await get_db()
    cursor = await db.execute(
        "SELECT full_name, phone FROM users WHERE telegram_id = ?", (telegram_id,)
    )
    user = await cursor.fetchone()

    cart_cursor = await db.execute(
        "SELECT COUNT(*) FROM cart_items WHERE telegram_id = ?", (telegram_id,)
    )
    cart_count = (await cart_cursor.fetchone())[0]
    await db.close()

    if cart_count == 0:
        keyboard = [[InlineKeyboardButton("Browse Products", callback_data="browse")]]
        await query.edit_message_text("Your cart is empty!", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    if user:
        context.user_data["checkout_name"] = user[0]
        context.user_data["checkout_phone"] = user[1]

    await query.edit_message_text(
        "Checkout\n━━━━━━━━━━━━━━━━━━\n\n"
        f"Name: {user[0] if user else 'Not set'}\n\n"
        "Please enter your full name for this order\n"
        "(or send the same name to confirm):"
    )
    return CHECKOUT_NAME


async def checkout_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Please enter your phone number for this order:"
    )
    return CHECKOUT_PHONE


async def checkout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data["checkout_phone"] = update.message.contact.phone_number
    else:
        context.user_data["checkout_phone"] = update.message.text.strip()
    await update.message.reply_text(
        "Please enter your delivery address:\n"
        "(Type 'self' if you'll collect in person)"
    )
    return CHECKOUT_ADDRESS


async def checkout_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    context.user_data["checkout_address"] = address

    if address.lower() == "self":
        context.user_data["delivery_method"] = "self_collection"
        context.user_data["delivery_fee"] = 0
        await show_order_summary(update, context)
        return ConversationHandler.END

    keyboard = []
    for key, opt in DELIVERY_OPTIONS.items():
        if key == "self_collection":
            continue
        fee_text = f"SGD {opt['fee']:.2f}" if opt['fee'] > 0 else "Free"
        keyboard.append([InlineKeyboardButton(
            f"{opt['label']} ({fee_text})", callback_data=f"delivery_{key}"
        )])

    await update.message.reply_text(
        "Select your delivery method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHECKOUT_DELIVERY


async def checkout_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_", 1)[1]
    context.user_data["delivery_method"] = method
    context.user_data["delivery_fee"] = DELIVERY_OPTIONS[method]["fee"]

    await show_order_summary_from_query(query, context)
    return ConversationHandler.END


async def show_order_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    db = await get_db()
    cursor = await db.execute(
        "SELECT p.name, ci.quantity, COALESCE(po.price, p.price), COALESCE(po.name, '') "
        "FROM cart_items ci "
        "JOIN products p ON ci.product_id = p.id "
        "LEFT JOIN package_options po ON ci.package_option_id = po.id "
        "WHERE ci.telegram_id = ?",
        (telegram_id,)
    )
    items = await cursor.fetchall()
    await db.close()

    subtotal = sum(item[2] * item[1] for item in items)
    delivery_fee = context.user_data.get("delivery_fee", 0)
    total = subtotal + delivery_fee
    delivery_method = context.user_data.get("delivery_method", "self_collection")
    delivery_label = DELIVERY_OPTIONS.get(delivery_method, {}).get("label", delivery_method)

    text = (
        "Order Summary\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Name: {context.user_data.get('checkout_name', 'N/A')}\n"
        f"Phone: {context.user_data.get('checkout_phone', 'N/A')}\n"
        f"Address: {context.user_data.get('checkout_address', 'Self Collection')}\n"
        f"Delivery: {delivery_label}\n\n"
        "Items:\n"
    )
    items_list = []
    for item in items:
        pkg = f" ({item[3]})" if item[3] else ""
        item_total = item[2] * item[1]
        text += f"  {item[0]}{pkg} x{item[1]} = SGD {item_total:.2f}\n"
        items_list.append({
            "name": item[0], "pkg": item[3], "qty": item[1], "price": item[2]
        })

    text += (
        f"\nSubtotal: SGD {subtotal:.2f}\n"
        f"Delivery: SGD {delivery_fee:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: SGD {total:.2f}\n\n"
        "Select payment method:"
    )

    context.user_data["order_items"] = items_list
    context.user_data["order_subtotal"] = subtotal
    context.user_data["order_total"] = total

    keyboard = [
        [InlineKeyboardButton("PayNow (QR Code)", callback_data="pay_paynow")],
        [InlineKeyboardButton("Credit/Debit Card (Stripe)", callback_data="pay_stripe")],
        [InlineKeyboardButton("Cancel Order", callback_data="main_menu")],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_order_summary_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = query.from_user.id
    db = await get_db()
    cursor = await db.execute(
        "SELECT p.name, ci.quantity, COALESCE(po.price, p.price), COALESCE(po.name, '') "
        "FROM cart_items ci "
        "JOIN products p ON ci.product_id = p.id "
        "LEFT JOIN package_options po ON ci.package_option_id = po.id "
        "WHERE ci.telegram_id = ?",
        (telegram_id,)
    )
    items = await cursor.fetchall()
    await db.close()

    subtotal = sum(item[2] * item[1] for item in items)
    delivery_fee = context.user_data.get("delivery_fee", 0)
    total = subtotal + delivery_fee
    delivery_method = context.user_data.get("delivery_method", "self_collection")
    delivery_label = DELIVERY_OPTIONS.get(delivery_method, {}).get("label", delivery_method)

    text = (
        "Order Summary\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Name: {context.user_data.get('checkout_name', 'N/A')}\n"
        f"Phone: {context.user_data.get('checkout_phone', 'N/A')}\n"
        f"Address: {context.user_data.get('checkout_address', 'Self Collection')}\n"
        f"Delivery: {delivery_label}\n\n"
        "Items:\n"
    )
    items_list = []
    for item in items:
        pkg = f" ({item[3]})" if item[3] else ""
        item_total = item[2] * item[1]
        text += f"  {item[0]}{pkg} x{item[1]} = SGD {item_total:.2f}\n"
        items_list.append({
            "name": item[0], "pkg": item[3], "qty": item[1], "price": item[2]
        })

    text += (
        f"\nSubtotal: SGD {subtotal:.2f}\n"
        f"Delivery: SGD {delivery_fee:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: SGD {total:.2f}\n\n"
        "Select payment method:"
    )

    context.user_data["order_items"] = items_list
    context.user_data["order_subtotal"] = subtotal
    context.user_data["order_total"] = total

    keyboard = [
        [InlineKeyboardButton("PayNow (QR Code)", callback_data="pay_paynow")],
        [InlineKeyboardButton("Credit/Debit Card (Stripe)", callback_data="pay_stripe")],
        [InlineKeyboardButton("Cancel Order", callback_data="main_menu")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    payment_method = query.data.split("_")[1]

    total = context.user_data.get("order_total", 0)
    items_list = context.user_data.get("order_items", [])

    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO orders (telegram_id, full_name, phone, address, delivery_method, "
        "delivery_fee, subtotal, total, payment_method, payment_status, order_status, items_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            telegram_id,
            context.user_data.get("checkout_name", ""),
            context.user_data.get("checkout_phone", ""),
            context.user_data.get("checkout_address", ""),
            context.user_data.get("delivery_method", ""),
            context.user_data.get("delivery_fee", 0),
            context.user_data.get("order_subtotal", 0),
            total,
            payment_method,
            "pending",
            "pending",
            json.dumps(items_list),
        )
    )
    order_id = cursor.lastrowid
    await db.execute("DELETE FROM cart_items WHERE telegram_id = ?", (telegram_id,))
    await db.commit()
    await db.close()

    if payment_method == "paynow":
        await query.edit_message_text(
            f"Order #{order_id} Created!\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"Total: SGD {total:.2f}\n\n"
            "Please scan the PayNow QR code below to complete payment.\n"
            "Once you have paid, tap the 'I Have Paid' button."
        )

        keyboard = [
            [InlineKeyboardButton("I Have Paid", callback_data=f"paid_{order_id}")],
            [InlineKeyboardButton("Cancel Order", callback_data=f"cancel_order_{order_id}")],
        ]
        await context.bot.send_photo(
            chat_id=telegram_id,
            photo=open(PAYNOW_QR_PATH, "rb"),
            caption=f"PayNow QR Code\nOrder #{order_id} - SGD {total:.2f}\n\nScan this QR code with your banking app to pay.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text(
            f"Order #{order_id} Created!\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"Total: SGD {total:.2f}\n\n"
            "Stripe payment is coming soon.\n"
            "Please use PayNow for now."
        )
        keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
        await context.bot.send_message(
            chat_id=telegram_id,
            text="To pay, please go back and select PayNow.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    if ADMIN_CHAT_ID:
        items_text = "\n".join(
            f"  - {i['name']} x{i['qty']} @ SGD {i['price']:.2f}"
            for i in items_list
        )
        admin_text = (
            f"NEW ORDER #{order_id}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Customer: {context.user_data.get('checkout_name', 'N/A')}\n"
            f"Phone: {context.user_data.get('checkout_phone', 'N/A')}\n"
            f"Address: {context.user_data.get('checkout_address', 'N/A')}\n"
            f"Delivery: {context.user_data.get('delivery_method', 'N/A')}\n\n"
            f"Items:\n{items_text}\n\n"
            f"Total: SGD {total:.2f}\n"
            f"Payment: {payment_method.upper()}\n"
            f"Status: Awaiting payment"
        )
        admin_keyboard = [
            [InlineKeyboardButton("Confirm Payment", callback_data=f"admin_confirm_{order_id}"),
             InlineKeyboardButton("Reject", callback_data=f"admin_reject_{order_id}")],
        ]
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID), text=admin_text,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")


async def handle_paid_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    order_id = int(query.data.split("_")[1])

    db = await get_db()
    await db.execute(
        "UPDATE orders SET payment_status = 'submitted' WHERE id = ? AND telegram_id = ?",
        (order_id, telegram_id),
    )
    await db.commit()
    await db.close()

    await query.edit_message_caption(
        caption=(
            f"Order #{order_id}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Thank you! Your payment has been submitted.\n"
            "We will verify and confirm your order shortly.\n\n"
            "You can check your order status anytime from the menu."
        ),
    )

    keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
    await context.bot.send_message(
        chat_id=telegram_id,
        text="Payment submitted! We'll confirm your order once verified.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    if ADMIN_CHAT_ID:
        admin_keyboard = [
            [InlineKeyboardButton("Confirm Payment", callback_data=f"admin_confirm_{order_id}"),
             InlineKeyboardButton("Reject", callback_data=f"admin_reject_{order_id}")],
        ]
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=f"PAYMENT SUBMITTED for Order #{order_id}\nCustomer says they have paid. Please verify and confirm.",
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin of payment: {e}")


async def handle_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    order_id = int(query.data.split("_")[2])

    db = await get_db()
    await db.execute(
        "UPDATE orders SET order_status = 'cancelled', payment_status = 'cancelled' "
        "WHERE id = ? AND telegram_id = ?",
        (order_id, telegram_id),
    )
    await db.commit()
    await db.close()

    await query.edit_message_caption(
        caption=f"Order #{order_id} has been cancelled.",
    )

    keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
    await context.bot.send_message(
        chat_id=telegram_id,
        text="Order cancelled. You can start a new order anytime.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    action = parts[1]
    order_id = int(parts[2])

    db = await get_db()
    cursor = await db.execute(
        "SELECT telegram_id, total, full_name FROM orders WHERE id = ?", (order_id,)
    )
    order = await cursor.fetchone()

    if not order:
        await query.edit_message_text(f"Order #{order_id} not found.")
        await db.close()
        return

    customer_telegram_id = order[0]
    total = order[1]
    customer_name = order[2]

    if action == "confirm":
        await db.execute(
            "UPDATE orders SET payment_status = 'paid', order_status = 'processing' WHERE id = ?",
            (order_id,),
        )
        await db.commit()
        await query.edit_message_text(
            query.message.text + f"\n\nPAYMENT CONFIRMED by admin."
        )
        try:
            keyboard = [[InlineKeyboardButton("View Orders", callback_data="my_orders")]]
            await context.bot.send_message(
                chat_id=customer_telegram_id,
                text=(
                    f"Order #{order_id} - Payment Confirmed!\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"Your payment of SGD {total:.2f} has been verified.\n"
                    "Your order is now being processed.\n\n"
                    "Thank you for your purchase!"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")

    elif action == "reject":
        await db.execute(
            "UPDATE orders SET payment_status = 'rejected', order_status = 'cancelled' WHERE id = ?",
            (order_id,),
        )
        await db.commit()
        await query.edit_message_text(
            query.message.text + f"\n\nPAYMENT REJECTED by admin."
        )
        try:
            keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
            await context.bot.send_message(
                chat_id=customer_telegram_id,
                text=(
                    f"Order #{order_id} - Payment Issue\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    "We could not verify your payment. "
                    "Please contact support if you believe this is an error."
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")

    await db.close()


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id

    db = await get_db()
    cursor = await db.execute(
        "SELECT id, total, order_status, payment_status, created_at "
        "FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 10",
        (telegram_id,)
    )
    orders = await cursor.fetchall()
    await db.close()

    if not orders:
        keyboard = [[InlineKeyboardButton("Main Menu", callback_data="main_menu")]]
        await query.edit_message_text("You have no orders yet.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_icons = {
        "pending": "Pending",
        "processing": "Processing",
        "shipped": "Shipped",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    text = "My Orders\n━━━━━━━━━━━━━━━━━━\n\n"
    for order in orders:
        status = status_icons.get(order[2], order[2])
        text += (
            f"Order #{order[0]}\n"
            f"  Total: SGD {order[1]:.2f}\n"
            f"  Status: {status}\n"
            f"  Payment: {order[3]}\n"
            f"  Date: {order[4]}\n\n"
        )

    keyboard = [[InlineKeyboardButton("Main Menu", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = await get_db()
    cursor = await db.execute("SELECT question, answer FROM faqs ORDER BY sort_order")
    faqs = await cursor.fetchall()
    await db.close()

    text = "Frequently Asked Questions\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, faq in enumerate(faqs, 1):
        text += f"Q{i}: {faq[0]}\nA: {faq[1]}\n\n"

    keyboard = [
        [InlineKeyboardButton("Contact Support", callback_data="support")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Customer Support\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Please type your question or concern below.\n"
        "Our team will get back to you as soon as possible.\n\n"
        "Type /cancel to go back to the menu."
    )
    return ENQUIRY_MSG


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    message = update.message.text.strip()

    db = await get_db()
    await db.execute(
        "INSERT INTO enquiries (telegram_id, message) VALUES (?, ?)",
        (telegram_id, message)
    )
    await db.commit()
    await db.close()

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=f"NEW ENQUIRY from user {telegram_id}:\n{message}"
            )
        except Exception:
            pass

    keyboard = [[InlineKeyboardButton("Main Menu", callback_data="main_menu")]]
    await update.message.reply_text(
        "Thank you! Your enquiry has been submitted.\n"
        "Our team will respond shortly.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)
    return ConversationHandler.END


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)


def build_app():
    app = Application.builder().token(BOT_TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE: [
                MessageHandler(filters.CONTACT, reg_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
            ],
            REG_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_country)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    checkout_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            CHECKOUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_name)],
            CHECKOUT_PHONE: [
                MessageHandler(filters.CONTACT, checkout_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_phone),
            ],
            CHECKOUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_address)],
            CHECKOUT_DELIVERY: [CallbackQueryHandler(checkout_delivery, pattern="^delivery_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    support_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(support_start, pattern="^support$")],
        states={
            ENQUIRY_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(reg_handler)
    app.add_handler(checkout_handler)
    app.add_handler(support_handler)
    app.add_handler(CommandHandler("menu", menu_command))

    app.add_handler(CallbackQueryHandler(browse_categories, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(show_category_products, pattern=r"^cat_\d+$"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern=r"^prod_\d+$"))
    app.add_handler(CallbackQueryHandler(show_product_full_info, pattern=r"^fullinfo_\d+$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern=r"^add_\d+$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern=r"^addpkg_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(show_cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(update_cart_item, pattern=r"^cart(inc|dec|del)_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern=r"^pay_"))
    app.add_handler(CallbackQueryHandler(handle_paid_confirmation, pattern=r"^paid_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_order, pattern=r"^cancel_order_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_admin_order_action, pattern=r"^admin_(confirm|reject)_\d+$"))
    app.add_handler(CallbackQueryHandler(show_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(show_faq, pattern="^faq$"))
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))

    return app


if __name__ == "__main__":
    import asyncio
    from database import init_db, seed_demo_data

    async def main():
        await init_db()
        await seed_demo_data()
        app = build_app()
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Bot is running...")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    asyncio.run(main())
