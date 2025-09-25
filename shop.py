from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bson import ObjectId
import random
import datetime

# --- Import database connections from utils.py ---
from utils import master_cards, p2p_listings, users, db

# --- Daily shop collection ---
if db is not None:
    daily_shop = db.daily_shop
else:
    daily_shop = None

# --- Rarity Mapping & Pricing ---
RARITY_MAP = {
    1: ("Common", "⚪️"),
    2: ("Uncommon", "🟢"),
    3: ("Rare", "🔵"),
    4: ("Epic", "🟣"),
    5: ("Legendary", "🟡"),
    6: ("Mythic", "🏵"),
    7: ("Retro", "🍥"),
    8: ("Zenith", "🪩"),
    9: ("Limited Edition", "🍬")  # excluded from shop
}

RARITY_ORDER = [1, 2, 3, 4, 5, 6, 7, 8]

RARITY_PRICE_RANGES = {
    "Common": (5, 15),
    "Uncommon": (15, 30),
    "Rare": (30, 60),
    "Epic": (60, 120),
    "Legendary": (120, 200),
    "Mythic": (50, 100),
    "Retro": (250, 300),
    "Zenith": (1000, 1200),
}

# --- Utility functions ---
def get_rarity_emoji(rarity):
    for _, (name, emoji) in RARITY_MAP.items():
        if name == rarity:
            return emoji
    return "❓"

def get_rarity_color_text(rarity):
    colors = {
        "Common": "<i>Simple & charming</i>",
        "Uncommon": "<i>Something special</i>",
        "Rare": "<i>Hard to find</i>",
        "Epic": "<i>Truly exceptional</i>",
        "Legendary": "<i>A living legend</i>",
        "Mythic": "<i>Once in a lifetime</i>",
        "Retro": "<i>Old but gold</i>",
        "Zenith": "<i>Peak rarity</i>",
        "Limited Edition": "<i>Special release</i>",
    }
    return colors.get(rarity, "<i>Mysterious</i>")

# Use utils.get_user and utils.create_user instead of duplicating user creation logic

# --- Shop Logic ---
def get_daily_shop_items():
    if daily_shop is None:
        return []  # Demo mode - no database available
    today = datetime.date.today().isoformat()
    shop = daily_shop.find_one({"date": today})
    if shop:
        return shop["cards"]

    cards = []
    for rarity_num in RARITY_ORDER:
        rarity_name, _ = RARITY_MAP[rarity_num]
        # Search for uppercase rarity to match database format
        available_cards = list(master_cards.find({"rarity": rarity_name.upper()}))
        
        if available_cards:
            # Select a random card from available cards
            card = random.choice(available_cards)
            low, high = RARITY_PRICE_RANGES[rarity_name]
            card["price"] = random.randint(low, high)
            cards.append(card)

    daily_shop.update_one(
        {"date": today},
        {"$set": {"cards": cards, "date": today}},
        upsert=True
    )
    return cards

def buy_from_default_shop(user_id, card_id):
    from utils import get_user, create_user
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
    today = datetime.date.today().isoformat()
    shop = daily_shop.find_one({"date": today})
    if not shop:
        return False, "Shop not available."

    card = next((c for c in shop["cards"] if c["card_id"] == card_id), None)
    if not card:
        return False, "Card not in today’s shop."

    if user['wish_balance'] < card['price']:
        return False, "Not enough currency."

    users.update_one(
        {"user_id": user_id},
        {"$inc": {"wish_balance": -card['price']}, "$push": {"collection": card_id}}
    )
    return True, card

# --- P2P Logic ---
def create_p2p_listing(user_id, card_id, price):
    from utils import get_user, create_user
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
    if card_id not in user.get("collection", []):
        return None, "You don't own this card."

    listing = {
        "seller_id": user_id,
        "card_id": card_id,
        "price": price,
        "is_active": True,
        "created_at": datetime.datetime.utcnow()
    }
    result = p2p_listings.insert_one(listing)
    return result.inserted_id, "Success"

def buy_from_p2p(buyer_id, listing_id):
    if p2p_listings is None:
        return False, "P2P marketplace not available in demo mode."
    listing = p2p_listings.find_one({"_id": listing_id, "is_active": True})
    if not listing:
        return False, "Listing not found."

    from utils import get_user, create_user
    buyer = get_user(buyer_id)
    if not buyer:
        create_user(buyer_id)
        buyer = get_user(buyer_id)
    seller = get_user(listing['seller_id'])
    if not seller:
        create_user(listing['seller_id'])
        seller = get_user(listing['seller_id'])
    if buyer['wish_balance'] < listing['price']:
        return False, "Not enough currency."

    # transfer currency and ownership
    users.update_one({"user_id": buyer_id}, {"$inc": {"wish_balance": -listing['price']}, "$push": {"collection": listing['card_id']}})
    users.update_one({"user_id": seller['user_id']}, {"$inc": {"wish_balance": listing['price']}, "$pull": {"collection": listing['card_id']}})
    p2p_listings.update_one({"_id": listing_id}, {"$set": {"is_active": False}})

    return True, listing

def get_p2p_listings():
    """Get all active P2P listings"""
    if p2p_listings is None:
        return []
    return list(p2p_listings.find({"is_active": True}))

# --- Telegram Handlers ---
async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shop_items = get_daily_shop_items()
    if not shop_items:
        await update.message.reply_text("🛒 The shop is empty! Come back later.")
        return

    # Build the formatted shop message
    shop_text = "✨ **DAILY WAIFU SHOP** ✨\n\n"
    
    for item in shop_items:
        rarity_emoji = get_rarity_emoji(item['rarity'])
        character_name = item['name']
        anime_name = item.get('series', 'Unknown')
        price = item['price']
        
        shop_text += f"{rarity_emoji} {character_name}\n"
        shop_text += f"       {anime_name}\n"
        shop_text += f"{price} 𝓒\n"
        shop_text += "---------------------\n"
    
    # Create buy buttons for all cards
    keyboard = []
    for item in shop_items:
        button_text = f"🛒 Buy {item['name']} - {item['price']} 𝓒"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"shop_buy_{item['card_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(shop_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if p2p_listings is None:
        await update.message.reply_text("🏪 **P2P Marketplace**\n\n⚠️ Marketplace is not available in demo mode. Please configure MONGODB_URL to enable trading features.")
        return
    listings = list(p2p_listings.find({"is_active": True}))
    if not listings:
        await update.message.reply_text("🏪 The marketplace is empty! Be the first to list something with /sell.")
        return

    await update.message.reply_text(f"🏪 **P2P MARKETPLACE** 🏪\n🤝 {len(listings)} Cards Listed!")
    for listing in listings[:10]:
        card = master_cards.find_one({"card_id": listing['card_id']}) or {"name": "Unknown", "rarity": "Unknown", "series": "Unknown", "image_url": ""}
        rarity_emoji = get_rarity_emoji(card['rarity'])
        rarity_color = get_rarity_color_text(card['rarity'])
        card_text = f"""
{rarity_emoji} <b>{card['name']}</b> {rarity_emoji}
{rarity_color}

📺 <b>Series:</b> {card.get('series', 'Unknown')}
💎 <b>Rarity:</b> {card['rarity']}
💰 <b>Price:</b> {listing['price']} 𝓒
🆔 <b>ID:</b> <code>{listing['card_id']}</code>
👤 <b>Seller:</b> {listing['seller_id']}
        """.strip()

        keyboard = [[InlineKeyboardButton(f"🛒 Buy {card['name']} - {listing['price']} 𝓒", callback_data=f"market_buy_{str(listing['_id'])}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if card.get('image_url'):
            await update.message.reply_photo(photo=card['image_url'], caption=card_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(card_text, reply_markup=reply_markup, parse_mode='HTML')

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /sell <card_id> <price>")
        return
    try:
        card_id, price = context.args[0], int(context.args[1])
        if price <= 0:
            await update.message.reply_text("Price must be positive!")
            return
        user_id = update.effective_user.id
        listing_id, msg = create_p2p_listing(user_id, card_id, price)
        if not listing_id:
            await update.message.reply_text(f"❌ {msg}")
            return
        await update.message.reply_text(f"✅ Listed {card_id} for {price} 𝓒 (ID: {listing_id})")
    except ValueError:
        await update.message.reply_text("Invalid price!")

async def handle_shop_purchase(query, card_id):
    from utils import get_user
    user_id = query.from_user.id
    success, result = buy_from_default_shop(user_id, card_id)
    if success:
        card = result
        user = get_user(user_id)
        await query.edit_message_text(f"✅ You bought {card['name']} ({card['rarity']}) for {card['price']} 𝓒. Balance: {user['wish_balance']} 𝓒")
    else:
        await query.edit_message_text(f"❌ {result}")

async def handle_market_purchase(query, listing_id):
    try:
        from utils import get_user
        buyer_id = query.from_user.id
        object_id = ObjectId(listing_id)
        success, result = buy_from_p2p(buyer_id, object_id)
        if success:
            buyer = get_user(buyer_id)
            await query.edit_message_text(f"✅ You bought {result['card_id']} for {result['price']} 𝓒. Balance: {buyer['wish_balance']} 𝓒")
        else:
            await query.edit_message_text(f"❌ {result}")
    except Exception:
        await query.edit_message_text("❌ Error processing purchase.")
