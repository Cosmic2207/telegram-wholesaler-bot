
import os
import logging
import sqlite3
from flask import Flask, request, Response
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '123456789'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')  # e.g. https://your-app.onrender.com
PORT = int(os.environ.get('PORT', '10000'))

# Flask app for health check
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return 'Bot is running!', 200

# Database functions
DB_NAME = 'wholesaler_bot.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Helper function to get product details
def get_product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return product

# Helper function to get cart items for a user
def get_cart_items(user_id):
    conn = get_db_connection()
    cart_items = conn.execute(
        """SELECT ci.id, p.id as product_id, p.name, p.price, ci.quantity FROM cart_items ci JOIN products p ON ci.product_id = p.id WHERE ci.user_id = ?""",
        (user_id,)
    ).fetchall()
    conn.close()
    return cart_items

# Helper function to calculate cart total
def get_cart_total(user_id):
    conn = get_db_connection()
    total = conn.execute(
        """SELECT SUM(p.price * ci.quantity) FROM cart_items ci JOIN products p ON ci.product_id = p.id WHERE ci.user_id = ?""",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return total if total else 0

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("Help & Info", callback_data="help_info")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        f"Hi {user.mention_html()}! Welcome to the Wholesaler Shop Bot. How can I help you today?",
        reply_markup=reply_markup,
    )

# Browse Products command
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    conn = get_db_connection()
    categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()
    conn.close()

    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category['category'], callback_data=f"show_category_{category['category']}")])
    keyboard.append([InlineKeyboardButton("Back to Main Menu", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Please select a category:", reply_markup=reply_markup)

# Show products by category
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    category = query.data.replace("show_category_", "")

    conn = get_db_connection()
    products = conn.execute('SELECT id, name, price FROM products WHERE category = ?', (category,)).fetchall()
    conn.close()

    keyboard = []
    for product in products:
        keyboard.append([InlineKeyboardButton(f"{product['name']} - ${product['price']:.2f}", callback_data=f"show_product_{product['id']}")])
    keyboard.append([InlineKeyboardButton("Back to Categories", callback_data="browse_products")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"Products in {category}:", reply_markup=reply_markup)

# Show single product details
async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("show_product_", ""))

    product = get_product(product_id)

    if product:
        message_text = (
            f"<b>{product['name']}</b>\n"
            f"<i>Category:</i> {product['category']}\n"
            f"<i>Description:</i> {product['description']}\n"
            f"<i>Price:</i> ${product['price']:.2f}\n"
            f"<i>In Stock:</i> {product['stock']}"
        )
        keyboard = [
            [InlineKeyboardButton("Add to Cart", callback_data=f"add_to_cart_{product['id']}")],
            [InlineKeyboardButton("Back to Products", callback_data=f"show_category_{product['category']}")],
            [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query.edit_message_text("Product not found.")

# Add to cart
async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_id = int(query.data.replace("add_to_cart_", ""))

    product = get_product(product_id)
    if not product:
        await query.edit_message_text("Product not found.")
        return

    if product['stock'] <= 0:
        await query.edit_message_text("Sorry, this item is out of stock.")
        return

    conn = get_db_connection()
    # Ensure user has a cart entry
    conn.execute('INSERT OR IGNORE INTO carts (user_id) VALUES (?)', (user_id,))
    # Check if item is already in cart
    cart_item = conn.execute(
        'SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?',
        (user_id, product_id)
    ).fetchone()

    if cart_item:
        new_quantity = cart_item['quantity'] + 1
        if new_quantity > product['stock']:
            await query.edit_message_text(f"Cannot add more than available stock ({product['stock']}). Current in cart: {cart_item['quantity']}")
            conn.close()
            return
        conn.execute(
            'UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?',
            (new_quantity, user_id, product_id)
        )
    else:
        conn.execute(
            'INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, 1)',
            (user_id, product_id)
        )
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("Continue Shopping", callback_data=f"show_category_{product['category']}")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"{product['name']} added to cart!", reply_markup=reply_markup)

# View Cart
async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cart_items = get_cart_items(user_id)
    cart_total = get_cart_total(user_id)

    if not cart_items:
        keyboard = [
            [InlineKeyboardButton("Browse Products", callback_data="browse_products")],
            [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Your cart is empty.", reply_markup=reply_markup)
        return

    message_text = "<b>Your Cart:</b>\n\n"
    for item in cart_items:
        message_text += f"{item['name']} x {item['quantity']} = ${item['price'] * item['quantity']:.2f}\n"
    message_text += f"\n<b>Total: ${cart_total:.2f}</b>"

    keyboard = [
        [InlineKeyboardButton("Checkout", callback_data="checkout")],
        [InlineKeyboardButton("Clear Cart", callback_data="clear_cart")],
        [InlineKeyboardButton("Continue Shopping", callback_data="browse_products")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")

# Clear Cart
async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = get_db_connection()
    conn.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Your cart has been cleared.", reply_markup=reply_markup)

# Checkout - Request delivery details
async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cart_items = get_cart_items(user_id)
    if not cart_items:
        await query.edit_message_text("Your cart is empty. Please add items before checking out.")
        return

    await query.edit_message_text("Please reply with your delivery details (Name, Address, Phone Number):")
    context.user_data['state'] = 'awaiting_delivery_details'

# Handle delivery details and place order
async def handle_delivery_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if context.user_data.get('state') == 'awaiting_delivery_details':
        delivery_details = update.message.text
        cart_items = get_cart_items(user_id)
        cart_total = get_cart_total(user_id)

        if not cart_items:
            await update.message.reply_text("Your cart is empty. Please add items before placing an order.")
            context.user_data['state'] = None
            return

        conn = get_db_connection()
        try:
            # Create new order
            cursor = conn.execute(
                'INSERT INTO orders (user_id, delivery_details, status) VALUES (?, ?, ?)',
                (user_id, delivery_details, 'Pending')
            )
            order_id = cursor.lastrowid

            # Add cart items to order items and update product stock
            for item in cart_items:
                product = get_product(item["product_id"])
                if product:
                    conn.execute(
                        'INSERT INTO order_items (order_id, product_id, quantity, price_at_order) VALUES (?, ?, ?, ?)',
                        (order_id, product['id'], item['quantity'], product['price'])
                    )
                    # Decrease stock
                    conn.execute(
                        'UPDATE products SET stock = stock - ? WHERE id = ?',
                        (item['quantity'], product['id'])
                    )

            # Clear user's cart
            conn.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
            conn.commit()

            order_confirmation_text = (
                f"<b>Order #{order_id} Placed Successfully!</b>\n\n"
                f"<i>Delivery Details:</i>\n{delivery_details}\n\n"
                f"<i>Items:</i>\n"
            )
            for item in cart_items:
                order_confirmation_text += f"{item['name']} x {item['quantity']} = ${item['price'] * item['quantity']:.2f}\n"
            order_confirmation_text += f"\n<b>Total: ${cart_total:.2f}</b>\n\n"
            order_confirmation_text += "We will process your order shortly."

            await update.message.reply_html(order_confirmation_text)

            # Notify admin
            admin_message = (
                f"<b>New Order #{order_id} Received!</b>\n"
                f"<i>User ID:</i> {user_id}\n"
                f"<i>Delivery Details:</i>\n{delivery_details}\n\n"
                f"<i>Items:</i>\n"
            )
            for item in cart_items:
                admin_message += f"{item['name']} x {item['quantity']} = ${item['price'] * item['quantity']:.2f}\n"
            admin_message += f"\n<b>Total: ${cart_total:.2f}</b>\n"
            admin_message += f"Status: Pending\n"
            admin_message += f"Use /admin_view_orders to manage."

            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message, parse_mode="HTML")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error placing order for user {user_id}: {e}")
            await update.message.reply_text("There was an error placing your order. Please try again later.")
        finally:
            conn.close()

        context.user_data['state'] = None
    else:
        # If not in awaiting_delivery_details state, treat as regular message
        await update.message.reply_text("I'm not sure how to respond to that. Please use the menu buttons.")

# My Orders
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = get_db_connection()
    orders = conn.execute('SELECT id, delivery_details, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()

    if not orders:
        keyboard = [
            [InlineKeyboardButton("Browse Products", callback_data="browse_products")],
            [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("You have no past orders.", reply_markup=reply_markup)
        return

    message_text = "<b>Your Orders:</b>\n\n"
    for order in orders:
        message_text += (
            f"<b>Order #{order['id']}</b> (<i>{order['status']}</i>)\n"
            f"<i>Placed On:</i> {order['created_at']}\n"
            f"<i>Delivery To:</i> {order['delivery_details'].split(chr(10))[0]}\n"
        )
        # Get order items for this order
        conn = get_db_connection()
        order_items = conn.execute(
            """SELECT p.name, oi.quantity, oi.price_at_order FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?""",
            (order['id'],)
        ).fetchall()
        conn.close()
        total_price = sum(item['quantity'] * item['price_at_order'] for item in order_items)
        message_text += f"<i>Total:</i> ${total_price:.2f}\n\n"

    keyboard = [
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")

# Help & Info
async def help_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    info_text = (
        "<b>Welcome to the Wholesaler Shop Bot!</b>\n\n"
        "Here are some common queries:\n\n"
        "<b>Store Hours:</b> We operate 24/7 online! For customer service, our team is available Monday-Friday, 9 AM - 5 PM (local time).\n\n"
        "<b>Delivery Information:</b> We offer delivery within 2-3 business days for local orders. International shipping times vary. Shipping costs are calculated at checkout.\n\n"
        "<b>Payment Methods:</b> We accept major credit cards, bank transfers, and PayPal. Details will be provided upon order confirmation.\n\n"
        "If you have any other questions, please contact our support team."
    )

    keyboard = [
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode="HTML")

# Admin Commands
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use admin commands.")
        return

    keyboard = [
        [InlineKeyboardButton("View Pending Orders", callback_data="admin_view_pending_orders")],
        [InlineKeyboardButton("View All Orders", callback_data="admin_view_all_orders")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome, Admin!", reply_markup=reply_markup)

async def admin_view_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("You are not authorized to use admin commands.")
        return

    conn = get_db_connection()
    orders = conn.execute('SELECT id, user_id, delivery_details, created_at FROM orders WHERE status = ? ORDER BY created_at ASC', ('Pending',)).fetchall()
    conn.close()

    if not orders:
        keyboard = [
            [InlineKeyboardButton("Back to Admin Menu", callback_data="admin_start")],
            [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("No pending orders.", reply_markup=reply_markup)
        return

    message_text = "<b>Pending Orders:</b>\n\n"
    order_keyboards = []
    for order in orders:
        oid = order['id']
        uid = order['user_id']
        created = order['created_at']
        delivery_first_line = order['delivery_details'].split(chr(10))[0]
        message_text += (
            f"<b>Order #{oid}</b> (<i>User: {uid}</i>)\n"
            f"<i>Placed On:</i> {created}\n"
            f"<i>Delivery To:</i> {delivery_first_line}\n\n"
        )
        order_keyboards.append([InlineKeyboardButton(f"Manage Order #{oid}", callback_data=f"admin_order_details_{oid}")])

    keyboard = order_keyboards + [
        [InlineKeyboardButton("Back to Admin Menu", callback_data="admin_start")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")

async def admin_view_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("You are not authorized to use admin commands.")
        return

    conn = get_db_connection()
    orders = conn.execute('SELECT id, user_id, delivery_details, status, created_at FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()

    if not orders:
        keyboard = [
            [InlineKeyboardButton("Back to Admin Menu", callback_data="admin_start")],
            [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("No orders found.", reply_markup=reply_markup)
        return

    message_text = "<b>All Orders:</b>\n\n"
    for order in orders:
        message_text += (
            f"<b>Order #{order['id']}</b> (<i>User: {order['user_id']}</i>)\n"
            f"<i>Status:</i> {order['status']}\n"
            f"<i>Placed On:</i> {order['created_at']}\n"
            f"<i>Delivery To:</i> {order['delivery_details'].split(chr(10))[0]}\n\n"
        )
    keyboard = [
        [InlineKeyboardButton("Back to Admin Menu", callback_data="admin_start")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")

async def admin_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("You are not authorized to use admin commands.")
        return

    order_id = int(query.data.replace("admin_order_details_", ""))

    conn = get_db_connection()
    order = conn.execute('SELECT id, user_id, delivery_details, status, created_at FROM orders WHERE id = ?', (order_id,)).fetchone()
    order_items = conn.execute(
        """SELECT p.name, oi.quantity, oi.price_at_order FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?""",
        (order_id,)
    ).fetchall()
    conn.close()

    if not order:
        await query.edit_message_text("Order not found.")
        return

    message_text = (
        f"<b>Order Details #{order['id']}</b>\n\n"
        f"<i>User ID:</i> {order['user_id']}\n"
        f"<i>Status:</i> {order['status']}\n"
        f"<i>Placed On:</i> {order['created_at']}\n"
        f"<i>Delivery Details:</i>\n{order['delivery_details']}\n\n"
        f"<i>Items:</i>\n"
    )
    total_price = 0
    for item in order_items:
        item_total = item['quantity'] * item['price_at_order']
        message_text += f"{item['name']} x {item['quantity']} = ${item_total:.2f}\n"
        total_price += item_total
    message_text += f"\n<b>Total: ${total_price:.2f}</b>"

    keyboard = [
        [InlineKeyboardButton("Mark as Confirmed", callback_data=f"admin_confirm_order_{order['id']}")],
        [InlineKeyboardButton("Mark as Delivered", callback_data=f"admin_deliver_order_{order['id']}")],
        [InlineKeyboardButton("Back to Pending Orders", callback_data="admin_view_pending_orders")],
        [InlineKeyboardButton("Back to Admin Menu", callback_data="admin_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode="HTML")

async def admin_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("You are not authorized to use admin commands.")
        return

    order_id = int(query.data.replace("admin_confirm_order_", ""))

    conn = get_db_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("Confirmed", order_id))
    conn.commit()

    await query.edit_message_text(f"Order #{order_id} marked as Confirmed.")
    # Optionally notify the user
    order = conn.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if order:
        await context.bot.send_message(chat_id=order['user_id'], text=f"Your Order #{order_id} has been Confirmed!")

async def admin_deliver_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("You are not authorized to use admin commands.")
        return

    order_id = int(query.data.replace("admin_deliver_order_", ""))

    conn = get_db_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("Delivered", order_id))
    conn.commit()

    await query.edit_message_text(f"Order #{order_id} marked as Delivered.")
    # Optionally notify the user
    order = conn.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if order:
        await context.bot.send_message(chat_id=order['user_id'], text=f"Your Order #{order_id} has been Delivered!")

# Initialize database and populate sample data on startup
def init_database():
    """Create tables and populate sample data if empty."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS carts (
        user_id INTEGER PRIMARY KEY
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES carts(user_id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        delivery_details TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price_at_order REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Check if products table is empty, populate sample data
    count = cursor.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    if count == 0:
        sample_products = [
            ('Organic Apples', 'Fresh, crisp organic apples (per kg)', 'Fruits', 3.50, 100),
            ('Bananas', 'Sweet and ripe bananas (per kg)', 'Fruits', 2.00, 150),
            ('Carrots', 'Locally sourced fresh carrots (per kg)', 'Vegetables', 1.80, 200),
            ('Potatoes', 'Versatile russet potatoes (per kg)', 'Vegetables', 1.20, 300),
            ('Milk (1L)', 'Full cream dairy milk', 'Dairy', 2.80, 50),
            ('Cheddar Cheese (250g)', 'Aged sharp cheddar cheese', 'Dairy', 5.00, 30),
            ('Whole Wheat Bread', 'Freshly baked whole wheat loaf', 'Bakery', 3.20, 40),
            ('Eggs (Dozen)', 'Farm fresh large eggs', 'Pantry', 4.00, 60),
            ('Rice (5kg)', 'Premium long-grain rice', 'Pantry', 8.00, 70),
            ('Chicken Breast (1kg)', 'Boneless, skinless chicken breast', 'Meat', 12.00, 25)
        ]
        cursor.executemany(
            'INSERT INTO products (name, description, category, price, stock) VALUES (?, ?, ?, ?, ?)',
            sample_products
        )
        logger.info('Sample products populated.')
    
    conn.commit()
    conn.close()
    logger.info('Database initialized successfully.')

# Main function
def main() -> None:
    """Start the bot."""
    # Initialize database on startup
    init_database()
    
    application = Application.builder().token(BOT_TOKEN).build()

    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(browse_products, pattern="^browse_products$"))
    application.add_handler(CallbackQueryHandler(show_category, pattern="^show_category_.*"))
    application.add_handler(CallbackQueryHandler(show_product, pattern="^show_product_.*"))
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_to_cart_.*"))
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(clear_cart, pattern="^clear_cart$"))
    application.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    application.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(help_info, pattern="^help_info$"))

    # Admin commands
    application.add_handler(CommandHandler("admin", admin_start))
    application.add_handler(CallbackQueryHandler(admin_start, pattern="^admin_start$"))
    application.add_handler(CallbackQueryHandler(admin_view_pending_orders, pattern="^admin_view_pending_orders$"))
    application.add_handler(CallbackQueryHandler(admin_view_all_orders, pattern="^admin_view_all_orders$"))
    application.add_handler(CallbackQueryHandler(admin_order_details, pattern="^admin_order_details_.*"))
    application.add_handler(CallbackQueryHandler(admin_confirm_order, pattern="^admin_confirm_order_.*"))
    application.add_handler(CallbackQueryHandler(admin_deliver_order, pattern="^admin_deliver_order_.*"))

    # Handle delivery details message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delivery_details))

    # Start Flask health check server in a background thread
    def run_flask():
        flask_app.run(host='0.0.0.0', port=PORT)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run the bot with polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
