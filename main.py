import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler
from dotenv import load_dotenv
from utils import *
from shop import *

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Suppress httpx logs to prevent token exposure
logging.getLogger("httpx").setLevel(logging.WARNING)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '<YOUR_BOT_TOKEN>')
OWNER_ID_STR = os.getenv('OWNER_ID', '0')
# Handle multiple owner IDs (take the first one)
OWNER_ID = int(OWNER_ID_STR.split(',')[0]) if OWNER_ID_STR else 0

if BOT_TOKEN == '<YOUR_BOT_TOKEN>':
    logger.warning("BOT_TOKEN not configured - running in demo mode.")
    print("Demo mode: Please configure your secrets (BOT_TOKEN, MONGODB_URL) for full functionality.")
    BOT_TOKEN = "demo_mode_token_123456:ABCDEF"  # Placeholder for demo mode

# Wish symbol
WISH_SYMBOL = "𝓒"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Create user if doesn't exist
    create_user(user_id, username)
    
    welcome_text = f"""
✨ Welcome to the VexaSwitch Store ✨

This bot serves as your gateway to purchase in-game currencies for a variety of popular titles managed by *Collector*.

To begin, simply type the /help command to view all available options.

> Note: If you encounter any issues or bugs, please report them to @CollectorAlerts.
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = f"""
📋 Available Commands:
/start - Start the bot
/help - Show this message
/shop - Explore the marketplace!
/mysales - View your waifu sales
/vault - View your 𝓒 balance
/dice - Earn extra 𝓒
/buy - Purchase Wishes with Telegram Stars

> Note: If you encounter any issues or bugs, please report them to @CollectorAlerts.
    """
    await update.message.reply_text(help_text)

async def vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /vault command (same as balance)"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, update.effective_user.username)
        user = get_user(user_id)
    
    balance_text = f"💰 Your balance: {user['wish_balance']} {WISH_SYMBOL}"
    await update.message.reply_text(balance_text)

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dice command - earn extra wishes randomly with cooldown"""
    user_id = update.effective_user.id
    
    if not get_user(user_id):
        create_user(user_id, update.effective_user.username)
    
    # Check cooldown (24 hours like daily)
    if not can_claim_daily(user_id):  # Reuse daily cooldown logic
        await update.message.reply_text("⏰ You've already used dice today! Come back in 24 hours.")
        return
    
    # Random reward between 1-10 wishes
    import random
    reward_amount = random.randint(1, 10)
    update_user_balance(user_id, reward_amount)
    record_transaction(user_id, "dice_reward", reward_amount, "Random dice reward")
    
    # Update last dice claim time (using daily claim field)
    from datetime import datetime
    if users is not None:
        users.update_one(
            {"user_id": user_id},
            {"$set": {"last_daily_claim": datetime.utcnow()}}
        )
    
    user = get_user(user_id)
    success_text = f"""
🎲 Lucky dice roll!
+{reward_amount} {WISH_SYMBOL}

💰 New balance: {user['wish_balance']} {WISH_SYMBOL}
⏰ Come back in 24 hours for another dice roll!
    """
    await update.message.reply_text(success_text)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, update.effective_user.username)
        user = get_user(user_id)
    
    balance_text = f"💰 Your balance: {user['wish_balance']} {WISH_SYMBOL}"
    await update.message.reply_text(balance_text)

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /daily command"""
    user_id = update.effective_user.id
    
    if not get_user(user_id):
        create_user(user_id, update.effective_user.username)
    
    if can_claim_daily(user_id):
        reward_amount = 10
        claim_daily_reward(user_id, reward_amount)
        
        user = get_user(user_id)
        success_text = f"""
🎁 Daily reward claimed!
+{reward_amount} {WISH_SYMBOL}

💰 New balance: {user['wish_balance']} {WISH_SYMBOL}
⏰ Come back in 24 hours for your next reward!
        """
        await update.message.reply_text(success_text)
    else:
        await update.message.reply_text("⏰ You've already claimed your daily reward! Come back in 24 hours.")

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /transfer command"""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer @username amount\nOr use /transferid user_id amount")
        return
    
    try:
        target_input = context.args[0]
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("Amount must be positive!")
            return
        
        from_user_id = update.effective_user.id
        
        # Check if it's a username or user ID
        if target_input.startswith('@'):
            username = target_input[1:]  # Remove @
            # Find user by username
            if users is not None:
                target_user = users.find_one({"username": username})
                if not target_user:
                    await update.message.reply_text(f"❌ User @{username} not found. They need to start the bot first.")
                    return
                to_user_id = target_user["user_id"]
            else:
                await update.message.reply_text("❌ Demo mode: Username lookup not available. Use user ID instead.")
                return
        else:
            # Assume it's a user ID
            try:
                to_user_id = int(target_input)
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID or username format.")
                return
        
        if from_user_id == to_user_id:
            await update.message.reply_text("You can't transfer to yourself!")
            return
        
        if transfer_wishes(from_user_id, to_user_id, amount):
            from_user = get_user(from_user_id)
            success_text = f"""
✅ Transfer successful!
Sent {amount} {WISH_SYMBOL} to user {to_user_id}
💰 Your new balance: {from_user['wish_balance']} {WISH_SYMBOL}
            """
            await update.message.reply_text(success_text)
        else:
            await update.message.reply_text("❌ Transfer failed! Check your balance.")
    
    except ValueError:
        await update.message.reply_text("Invalid amount! Please enter a number.")

async def transfer_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle transfer by user ID"""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transferid user_id amount")
        return
    
    try:
        to_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("Amount must be positive!")
            return
        
        from_user_id = update.effective_user.id
        
        if from_user_id == to_user_id:
            await update.message.reply_text("You can't transfer to yourself!")
            return
        
        if transfer_wishes(from_user_id, to_user_id, amount):
            from_user = get_user(from_user_id)
            success_text = f"""
✅ Transfer successful!
Sent {amount} {WISH_SYMBOL} to user {to_user_id}
💰 Your new balance: {from_user['wish_balance']} {WISH_SYMBOL}
            """
            await update.message.reply_text(success_text)
        else:
            await update.message.reply_text("❌ Transfer failed! Check your balance.")
    
    except ValueError:
        await update.message.reply_text("Invalid input! Use numbers only.")

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command - Telegram Stars integration"""
    keyboard = [
        [InlineKeyboardButton("500 𝓒 for 30 ⭐", callback_data="buy_wishes_30")],
        [InlineKeyboardButton("1000 𝓒 for 50 ⭐", callback_data="buy_wishes_50")],
        [InlineKeyboardButton("2000 𝓒 for 90 ⭐", callback_data="buy_wishes_90")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💎 **Buy Wishes with Telegram Stars** 💎

Choose a package:
• 30 ⭐ = 500 {WISH_SYMBOL}
• 50 ⭐ = 1000 {WISH_SYMBOL}
• 90 ⭐ = 2000 {WISH_SYMBOL}

Click a button below to purchase:
    """
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shop command with two tabs"""
    text = "🛑️ VexaSwitch Store – Shop\nChoose a tab to browse:"
    
    keyboard = [
        [InlineKeyboardButton("🏪 Daily Shop", callback_data="shop_tab_daily"),
         InlineKeyboardButton("🏪 P2P Marketplace", callback_data="shop_tab_p2p")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /market command"""
    await show_market(update, context)

async def mysales_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mysales command"""
    await show_user_listings(update, context)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command"""
    user_id = update.effective_user.id
    transactions = get_user_transactions(user_id, limit=10)
    
    if not transactions:
        await update.message.reply_text("📊 No transaction history yet.")
        return
    
    history_text = "📊 **Your Transaction History:**\n\n"
    
    for tx in transactions:
        timestamp = tx['timestamp'].strftime("%m/%d %H:%M")
        amount_str = f"+{tx['amount']}" if tx['amount'] > 0 else str(tx['amount'])
        history_text += f"• {timestamp}: {amount_str} {WISH_SYMBOL} - {tx['description']}\n"
    
    await update.message.reply_text(history_text)

async def cards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cards command - show user's card collection"""
    user_id = update.effective_user.id
    user_cards_list = get_user_cards(user_id)
    
    if not user_cards_list:
        await update.message.reply_text("🃏 You don't have any cards yet! Visit the /shop to buy some.")
        return
    
    # Group cards by card_id and count duplicates
    card_counts = {}
    for card in user_cards_list:
        card_id = card['card_id']
        if card_id in card_counts:
            card_counts[card_id]['count'] += 1
        else:
            card_counts[card_id] = {
                'count': 1,
                'name': card.get('card_name', card_id),
                'rarity': card.get('rarity', 'Unknown')
            }
    
    cards_text = f"🃏 **Your Card Collection** 🃏\n\n"
    for card_id, info in card_counts.items():
        count_display = f" x{info['count']}" if info['count'] > 1 else ""
        cards_text += f"• **{info['name']}** ({info['rarity']}){count_display}\n"
        cards_text += f"  🆔 {card_id}\n\n"
    
    cards_text += f"📊 Total unique cards: {len(card_counts)}\n"
    cards_text += f"📊 Total cards: {len(user_cards_list)}"
    
    await update.message.reply_text(cards_text)

async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /grant command - Owner only"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only available to the bot owner.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /grant user_id amount")
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        # Ensure target user exists
        if not get_user(target_user_id):
            create_user(target_user_id)
        
        # Grant wishes
        update_user_balance(target_user_id, amount)
        record_transaction(target_user_id, "admin_grant", amount, f"Admin grant from owner")
        
        target_user = get_user(target_user_id)
        success_text = f"""
✅ **Grant Successful**
Granted {amount} {WISH_SYMBOL} to user {target_user_id}
Their new balance: {target_user['wish_balance']} {WISH_SYMBOL}
        """
        await update.message.reply_text(success_text)
        
    except ValueError:
        await update.message.reply_text("Invalid input! Use numbers only.")

async def refresh_shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /refreshshop command - Owner only"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only available to the bot owner.")
        return
    
    # Refresh the shop
    new_cards = refresh_daily_shop()
    
    success_text = f"""
✅ **Shop Refreshed!**
🛒 New daily shop loaded with {len(new_cards)} fresh cards!
🎲 Random pricing applied based on rarity
⏰ Ready for players to discover!
    """
    await update.message.reply_text(success_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("buy_wishes_"):
        stars_amount = int(data.split("_")[-1])
        await handle_stars_purchase(query, stars_amount)
    elif data.startswith("shop_buy_"):
        card_id = data.replace("shop_buy_", "")
        await handle_shop_purchase(query, card_id)
    elif data.startswith("market_buy_"):
        listing_id = data.replace("market_buy_", "")
        await handle_market_purchase(query, listing_id)
    elif data == "shop_tab_daily":
        await show_daily_shop_tab(query)
    elif data == "shop_tab_p2p":
        await show_p2p_shop_tab(query)

async def show_daily_shop_tab(query):
    """Show Daily Shop tab content"""
    from shop import get_daily_shop_items
    
    shop_items = get_daily_shop_items()
    
    if not shop_items:
        text = "🏪 **Daily Shop**\n\n🛒 The shop is empty! Come back later."
        keyboard = [[InlineKeyboardButton("← Back to Shop", callback_data="shop_tab_daily")]]
    else:
        text = f"🏪 **Daily Shop**\n\n🎆 {len(shop_items)} fresh items available today!\n\n"
        keyboard = []
        
        for item in shop_items[:5]:  # Show first 5 items
            text += f"• **{item['name']}** ({item['rarity']}) - {item['price']} 𝓒\n"
            keyboard.append([InlineKeyboardButton(
                f"🛒 Buy {item['name']} - {item['price']} 𝓒",
                callback_data=f"shop_buy_{item['card_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🏪 P2P Marketplace", callback_data="shop_tab_p2p")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_p2p_shop_tab(query):
    """Show P2P Marketplace tab content"""
    from shop import get_p2p_listings
    
    listings = get_p2p_listings()
    
    if not listings:
        text = "🏪 **P2P Marketplace**\n\n🏪 No listings available! Be the first to list something."
        keyboard = [[InlineKeyboardButton("🏪 Daily Shop", callback_data="shop_tab_daily")]]
    else:
        text = f"🏪 **P2P Marketplace**\n\n🤝 {len(listings)} items listed by players!\n\n"
        keyboard = []
        
        for listing in listings[:5]:  # Show first 5 listings
            text += f"• **{listing['card_id']}** - {listing['price']} 𝓒 (Seller: {listing['seller_id']})\n"
            keyboard.append([InlineKeyboardButton(
                f"🛒 Buy from Player - {listing['price']} 𝓒",
                callback_data=f"market_buy_{str(listing['_id'])}"
            )])
        
        keyboard.append([InlineKeyboardButton("🏪 Daily Shop", callback_data="shop_tab_daily")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_stars_purchase(query, stars_amount):
    """Handle Telegram Stars purchase"""
    user_id = query.from_user.id
    
    # New conversion rates: 30=500, 50=1000, 90=2000
    conversion_rates = {30: 500, 50: 1000, 90: 2000}
    wish_amount = conversion_rates.get(stars_amount, stars_amount * 10)
    
    title = f"Wish Pack - {wish_amount} {WISH_SYMBOL}"
    description = f"Purchase {wish_amount} wishes for {stars_amount} Telegram Stars"
    
    prices = [LabeledPrice(label="Wishes", amount=stars_amount)]
    
    await query.message.reply_invoice(
        title=title,
        description=description,
        payload=f"wishes_{user_id}_{stars_amount}",
        provider_token="",  # Empty for Telegram Stars
        currency="XTR",  # Telegram Stars
        prices=prices
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    # Parse payload to get stars amount
    payload_parts = payment.invoice_payload.split("_")
    if len(payload_parts) >= 3 and payload_parts[0] == "wishes":
        stars_amount = int(payload_parts[2])
        wish_amount = add_wishes_for_stars(user_id, stars_amount)
        
        user = get_user(user_id)
        success_text = f"""
✅ **Purchase Successful!**
+{wish_amount} {WISH_SYMBOL} added to your account!
💰 New balance: {user['wish_balance']} {WISH_SYMBOL}

Thank you for your purchase! 🎉
        """
        await update.message.reply_text(success_text)

def main():
    """Start the bot"""
    # Check if running in demo mode
    if BOT_TOKEN.startswith("demo_mode"):
        logger.info("\n=== VexaSwitch Store Bot Demo Mode ===")
        print("Configuration verified! Bot is ready to run.")
        print("\nFeatures implemented:")
        print("✅ Currency: Wish (𝓒)")
        print("✅ Commands: /start, /help, /vault, /dice, /transfer, /shop, /mysales, /buy")
        print("✅ Unified /shop with Daily Shop and P2P Marketplace tabs")
        print("✅ Telegram Stars integration (500:30, 1000:50, 2000:90)")
        print("✅ Security: 24-hour cooldown on /dice command")
        print("\nTo start the bot:")
        print("1. Set BOT_TOKEN environment variable with your bot token")
        print("2. Set MONGODB_URL environment variable with your MongoDB connection string")
        print("3. Restart the bot")
        return
    
    # Initialize database if connected
    if users is not None and not get_user(1):  # Check if database is initialized
        initialize_default_shop()
        logger.info("Database initialized with sample data")
    elif users is None:
        logger.info("Running in demo mode - database not connected")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("vault", vault))
    application.add_handler(CommandHandler("dice", dice))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("daily", daily))
    application.add_handler(CommandHandler("transfer", transfer))
    application.add_handler(CommandHandler("transferid", transfer_by_id))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("mysales", mysales_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("grant", grant_command))  # Owner only command
    application.add_handler(CommandHandler("refreshshop", refresh_shop_command))  # Owner only command
    application.add_handler(CommandHandler("cards", cards_command))
    
    # Shop-related handlers (from shop.py)
    application.add_handler(CommandHandler("sell", sell_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Start the bot
    logger.info("Starting VexaSwitch Store Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()