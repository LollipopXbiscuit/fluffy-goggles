from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import *
from bson import ObjectId

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the default daily shop"""
    shop_items = get_default_shop_items()
    
    if not shop_items:
        await update.message.reply_text("🛒 The shop is empty! Come back later.")
        return
    
    text = "🛒 **Daily Waifu Shop** 🛒\n\n"
    keyboard = []
    
    for item in shop_items:
        text += f"🃏 **{item['name']}** ({item['rarity']})\n"
        text += f"💰 Price: {item['price']} ☆W\n"
        text += f"🆔 ID: {item['card_id']}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"Buy {item['name']} - {item['price']} ☆W",
            callback_data=f"shop_buy_{item['card_id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display P2P marketplace"""
    listings = get_p2p_listings()
    
    if not listings:
        await update.message.reply_text("🏪 The marketplace is empty! Be the first to list something with /sell.")
        return
    
    text = "🏪 **P2P Marketplace** 🏪\n\n"
    keyboard = []
    
    for listing in listings[:10]:  # Show first 10 listings
        text += f"🃏 **{listing['card_id']}**\n"
        text += f"💰 Price: {listing['price']} ☆W\n"
        text += f"👤 Seller: {listing['seller_id']}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"Buy {listing['card_id']} - {listing['price']} ☆W",
            callback_data=f"market_buy_{str(listing['_id'])}"
        )])
    
    if len(listings) > 10:
        text += f"... and {len(listings) - 10} more items!"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_user_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current P2P listings"""
    user_id = update.effective_user.id
    listings = get_user_listings(user_id)
    
    if not listings:
        await update.message.reply_text("📦 You have no active listings. Use /sell to list a card!")
        return
    
    text = "📦 **Your Active Listings** 📦\n\n"
    keyboard = []
    
    for listing in listings:
        text += f"🃏 **{listing['card_id']}**\n"
        text += f"💰 Price: {listing['price']} ☆W\n"
        text += f"📅 Listed: {listing['created_at'].strftime('%m/%d/%Y')}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"Remove {listing['card_id']}", callback_data=f"remove_{str(listing['_id'])}"),
            InlineKeyboardButton(f"Edit Price", callback_data=f"edit_{str(listing['_id'])}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def buy_from_shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command for default shop"""
    if not context.args:
        await update.message.reply_text("Usage: /buy <card_id>")
        return
    
    card_id = context.args[0]
    user_id = update.effective_user.id
    
    success, result = buy_from_default_shop(user_id, card_id)
    
    if success:
        card = result
        user = get_user(user_id)
        success_text = f"""
✅ **Purchase Successful!**
🃏 You bought **{card['name']}** ({card['rarity']})
💰 Spent: {card['price']} ☆W
💰 New balance: {user['wish_balance']} ☆W

The card has been added to your collection! 🎉
        """
        await update.message.reply_text(success_text)
    else:
        await update.message.reply_text(f"❌ Purchase failed: {result}")

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sell command for P2P marketplace"""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /sell <card_id> <price>")
        return
    
    try:
        card_id = context.args[0]
        price = int(context.args[1])
        
        if price <= 0:
            await update.message.reply_text("Price must be positive!")
            return
        
        user_id = update.effective_user.id
        result = create_p2p_listing(user_id, card_id, price)
        
        if result[0] is None:
            # Error occurred
            await update.message.reply_text(f"❌ {result[1]}")
            return
        
        listing_id = result[0]
        success_text = f"""
✅ **Listing Created!**
🃏 Card: {card_id}
💰 Price: {price} ☆W
🆔 Listing ID: {listing_id}

Your card is now available in the marketplace! 🏪
        """
        await update.message.reply_text(success_text)
        
    except ValueError:
        await update.message.reply_text("Invalid price! Please enter a number.")

async def buyfrom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buyfrom command for P2P purchases"""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /buyfrom <seller_id> <card_id>")
        return
    
    try:
        seller_id = int(context.args[0])
        card_id = context.args[1]
        buyer_id = update.effective_user.id
        
        # Find the listing
        listing = p2p_listings.find_one({
            "seller_id": seller_id,
            "card_id": card_id,
            "is_active": True
        })
        
        if not listing:
            await update.message.reply_text("❌ Listing not found or no longer available.")
            return
        
        success, result = buy_from_p2p(buyer_id, listing['_id'])
        
        if success:
            listing_data = result
            buyer = get_user(buyer_id)
            success_text = f"""
✅ **Purchase Successful!**
🃏 You bought **{listing_data['card_id']}**
💰 Spent: {listing_data['price']} ☆W
💰 New balance: {buyer['wish_balance']} ☆W

The card has been transferred to your collection! 🎉
            """
            await update.message.reply_text(success_text)
        else:
            await update.message.reply_text(f"❌ Purchase failed: {result}")
            
    except ValueError:
        await update.message.reply_text("Invalid seller ID! Please enter a number.")

async def handle_shop_purchase(query, card_id):
    """Handle shop purchase from inline button"""
    user_id = query.from_user.id
    success, result = buy_from_default_shop(user_id, card_id)
    
    if success:
        card = result
        user = get_user(user_id)
        success_text = f"""
✅ **Purchase Successful!**
🃏 You bought **{card['name']}** ({card['rarity']})
💰 Spent: {card['price']} ☆W
💰 New balance: {user['wish_balance']} ☆W
        """
        await query.edit_message_text(success_text)
    else:
        await query.edit_message_text(f"❌ Purchase failed: {result}")

async def handle_market_purchase(query, listing_id):
    """Handle market purchase from inline button"""
    try:
        buyer_id = query.from_user.id
        object_id = ObjectId(listing_id)
        success, result = buy_from_p2p(buyer_id, object_id)
        
        if success:
            listing = result
            buyer = get_user(buyer_id)
            success_text = f"""
✅ **Purchase Successful!**
🃏 You bought **{listing['card_id']}**
💰 Spent: {listing['price']} ☆W
💰 New balance: {buyer['wish_balance']} ☆W
            """
            await query.edit_message_text(success_text)
        else:
            await query.edit_message_text(f"❌ Purchase failed: {result}")
            
    except Exception as e:
        await query.edit_message_text("❌ Error processing purchase.")