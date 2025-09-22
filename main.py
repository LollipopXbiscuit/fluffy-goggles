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

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # Set your user ID as owner

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables!")
    exit(1)

# Wish symbol
WISH_SYMBOL = "☆W"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Create user if doesn't exist
    create_user(user_id, username)
    
    welcome_text = f"""
🎉 Welcome to WishBot! 🎉

Your magical currency: {WISH_SYMBOL} (Wishes)

💫 **Commands:**
💰 /balance - Check your wish balance
🎁 /daily - Claim daily free wishes
💸 /transfer @user amount - Send wishes to others
🛒 /shop - Browse daily shop
🏪 /market - P2P marketplace
📦 /mysell - Manage your listings
💎 /buywishes - Buy wishes with Telegram Stars
📊 /history - View transaction history

🌟 Start by claiming your daily reward with /daily!
    """
    
    await update.message.reply_text(welcome_text)

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
        await update.message.reply_text("Usage: /transfer @username amount")
        return
    
    try:
        target_user = context.args[0].replace('@', '')
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("Amount must be positive!")
            return
        
        from_user_id = update.effective_user.id
        
        # Find target user by username (simplified - in real implementation you'd need user mapping)
        await update.message.reply_text("Note: For this demo, use user ID instead of username. Usage: /transfer user_id amount")
        
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

async def buywishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buywishes command - Telegram Stars integration"""
    keyboard = [
        [InlineKeyboardButton("10 ☆W for 1 ⭐", callback_data="buy_wishes_1")],
        [InlineKeyboardButton("50 ☆W for 5 ⭐", callback_data="buy_wishes_5")],
        [InlineKeyboardButton("100 ☆W for 10 ⭐", callback_data="buy_wishes_10")],
        [InlineKeyboardButton("500 ☆W for 50 ⭐", callback_data="buy_wishes_50")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💎 **Buy Wishes with Telegram Stars** 💎

Choose a package:
• 1 ⭐ = 10 {WISH_SYMBOL}
• 5 ⭐ = 50 {WISH_SYMBOL}
• 10 ⭐ = 100 {WISH_SYMBOL}
• 50 ⭐ = 500 {WISH_SYMBOL}

Click a button below to purchase:
    """
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shop command"""
    await show_shop(update, context)

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /market command"""
    await show_market(update, context)

async def mysell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mysell command"""
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

async def handle_stars_purchase(query, stars_amount):
    """Handle Telegram Stars purchase"""
    user_id = query.from_user.id
    wish_amount = stars_amount * 10  # Conversion rate: 1 star = 10 wishes
    
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
    # Initialize database
    if not get_user(1):  # Check if database is initialized
        initialize_default_shop()
        logger.info("Database initialized with sample data")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("daily", daily))
    application.add_handler(CommandHandler("transfer", transfer))
    application.add_handler(CommandHandler("transferid", transfer_by_id))
    application.add_handler(CommandHandler("buywishes", buywishes))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("mysell", mysell_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("grant", grant_command))  # Owner only command
    
    # Shop-related handlers (from shop.py)
    application.add_handler(CommandHandler("buy", buy_from_shop_command))
    application.add_handler(CommandHandler("sell", sell_command))
    application.add_handler(CommandHandler("buyfrom", buyfrom_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Start the bot
    logger.info("Starting WishBot...")
    application.run_polling()

if __name__ == '__main__':
    main()