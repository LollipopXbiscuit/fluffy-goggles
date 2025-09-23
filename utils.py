import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
mongo_uri = os.getenv('MONGODB_URL', '<YOUR_MONGO_URI>')
if mongo_uri == '<YOUR_MONGO_URI>':
    print("Warning: MongoDB URI not configured. Please set MONGODB_URL environment variable.")
    mongo_uri = None

if mongo_uri:
    client = MongoClient(mongo_uri)
else:
    client = None
if client:
    db = client.telegram_bot
    # Collections
    users = db.users
    transactions = db.transactions
    default_shop = db.default_shop
    p2p_listings = db.p2p_listings
    user_cards = db.user_cards
    master_cards = db.master_cards  # Master collection of all available waifu cards
else:
    db = users = transactions = default_shop = p2p_listings = user_cards = master_cards = None

def create_user(user_id, username=None):
    """Create a new user or return existing user"""
    if users is None:
        print("Database not connected - using placeholder data")
        return {"user_id": user_id, "username": username, "wish_balance": 100, "last_daily_claim": None}
    
    existing_user = users.find_one({"user_id": user_id})
    if existing_user:
        return existing_user
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "wish_balance": 200,
        "last_daily_claim": None,
        "dice_uses_today": 0,
        "last_dice_reset": datetime.utcnow().date().isoformat(),
        "created_at": datetime.utcnow()
    }
    users.insert_one(user_data)
    return user_data

def get_user(user_id):
    """Get user by ID"""
    if users is None:
        print("Database not connected - using placeholder data")
        return {"user_id": user_id, "wish_balance": 100, "last_daily_claim": None}
    return users.find_one({"user_id": user_id})

def update_user_balance(user_id, amount):
    """Update user's wish balance (can be positive or negative)"""
    if users is None:
        print(f"Database not connected - would update user {user_id} balance by {amount}")
        return True
        
    user = get_user(user_id)
    if not user:
        return False
    
    new_balance = user["wish_balance"] + amount
    if new_balance < 0:
        return False  # Prevent negative balance
    
    users.update_one(
        {"user_id": user_id},
        {"$set": {"wish_balance": new_balance}}
    )
    return True

def can_claim_daily(user_id):
    """Check if user can claim daily reward"""
    if users is None:
        print("Database not connected - allowing daily claim")
        return True
        
    user = get_user(user_id)
    if not user:
        return False
    
    if not user.get("last_daily_claim"):
        return True
    
    last_claim = user["last_daily_claim"]
    if isinstance(last_claim, str):
        last_claim = datetime.fromisoformat(last_claim)
    
    time_since_claim = datetime.utcnow() - last_claim
    return time_since_claim >= timedelta(hours=24)

def claim_daily_reward(user_id, amount=10):
    """Claim daily reward and update last claim time"""
    if not can_claim_daily(user_id):
        return False
    
    if users is None:
        print(f"Demo mode: Would claim {amount} daily reward for user {user_id}")
        return True
    
    users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"wish_balance": amount},
            "$set": {"last_daily_claim": datetime.utcnow()}
        }
    )
    
    # Record transaction
    record_transaction(user_id, "daily_reward", amount, "Daily reward claim")
    return True

def reset_all_vaults():
    """Reset all users' wish balances to 0"""
    if users is None:
        print("Database not connected - cannot reset vaults")
        return False
    
    try:
        result = users.update_many(
            {},  # Empty filter to match all documents
            {"$set": {"wish_balance": 0}}
        )
        print(f"Reset {result.modified_count} user vaults to 0")
        return True
    except Exception as e:
        print(f"Error resetting vaults: {e}")
        return False

def transfer_wishes(from_user_id, to_user_id, amount):
    """Transfer wishes between users"""
    if users is None:
        print(f"Demo mode: Would transfer {amount} wishes from {from_user_id} to {to_user_id}")
        return True
        
    from_user = get_user(from_user_id)
    if not from_user or from_user["wish_balance"] < amount:
        return False
    
    # Ensure target user exists
    create_user(to_user_id)
    
    # Perform transfer
    users.update_one({"user_id": from_user_id}, {"$inc": {"wish_balance": -amount}})
    users.update_one({"user_id": to_user_id}, {"$inc": {"wish_balance": amount}})
    
    # Record transactions
    record_transaction(from_user_id, "transfer_out", -amount, f"Transfer to user {to_user_id}")
    record_transaction(to_user_id, "transfer_in", amount, f"Transfer from user {from_user_id}")
    
    return True

def record_transaction(user_id, transaction_type, amount, description):
    """Record a transaction"""
    if transactions is None:
        print(f"Database not connected - would record transaction: {user_id} {transaction_type} {amount} {description}")
        return
        
    transaction = {
        "user_id": user_id,
        "type": transaction_type,
        "amount": amount,
        "description": description,
        "timestamp": datetime.utcnow()
    }
    transactions.insert_one(transaction)

def get_user_transactions(user_id, limit=10):
    """Get user's transaction history"""
    if transactions is None:
        # Return demo transactions for placeholder mode
        from datetime import datetime
        return [
            {"timestamp": datetime.utcnow(), "amount": 10, "description": "Demo transaction"},
            {"timestamp": datetime.utcnow(), "amount": -5, "description": "Demo purchase"}
        ]
    return list(transactions.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))

def add_wishes_for_stars(user_id, stars_amount, conversion_rate=10):
    """Add wishes when user buys with Telegram Stars"""
    wish_amount = stars_amount * conversion_rate
    update_user_balance(user_id, wish_amount)
    record_transaction(user_id, "stars_purchase", wish_amount, f"Purchased {wish_amount} wishes with {stars_amount} stars")
    return wish_amount

# Rarity pricing ranges
RARITY_PRICING = {
    "LIMITED EDITION": (3000, 4000),
    "ZENITH": (1000, 2000),
    "RETRO": (250, 300),
    "MYTHIC": (50, 100),
    "LEGENDARY": (25, 49),
    "EPIC": (15, 24),
    "RARE": (8, 14),
    "UNCOMMON": (3, 7),
    "COMMON": (1, 2)
}

def initialize_master_cards():
    """Initialize master cards database with comprehensive waifu collection"""
    # Only initialize if master cards collection is empty
    if master_cards.count_documents({}) > 0:
        print("Master cards already exist, skipping initialization")
        return
    
    print("Initializing master cards collection...")
    
    # Comprehensive waifu cards database
    master_waifu_cards = [
        # LIMITED EDITION
        {"card_id": "waifu_le_001", "name": "Goddess Asuna", "rarity": "LIMITED EDITION", "image_url": "", "series": "SAO"},
        {"card_id": "waifu_le_002", "name": "Divine Rem", "rarity": "LIMITED EDITION", "image_url": "", "series": "Re:Zero"},
        
        # ZENITH
        {"card_id": "waifu_z_001", "name": "Zenith Zero Two", "rarity": "ZENITH", "image_url": "", "series": "Darling in the FranXX"},
        {"card_id": "waifu_z_002", "name": "Zenith Makima", "rarity": "ZENITH", "image_url": "", "series": "Chainsaw Man"},
        {"card_id": "waifu_z_003", "name": "Zenith Violet", "rarity": "ZENITH", "image_url": "", "series": "Violet Evergarden"},
        
        # RETRO
        {"card_id": "waifu_r_001", "name": "Retro Sailor Moon", "rarity": "RETRO", "image_url": "https://i.imgur.com/placeholder6.jpg", "series": "Sailor Moon"},
        {"card_id": "waifu_r_002", "name": "Retro Bulma", "rarity": "RETRO", "image_url": "https://i.imgur.com/placeholder7.jpg", "series": "Dragon Ball"},
        {"card_id": "waifu_r_003", "name": "Retro Rei Ayanami", "rarity": "RETRO", "image_url": "https://i.imgur.com/placeholder8.jpg", "series": "Evangelion"},
        {"card_id": "waifu_r_004", "name": "Retro Akane", "rarity": "RETRO", "image_url": "https://i.imgur.com/placeholder9.jpg", "series": "Ranma 1/2"},
        
        # MYTHIC
        {"card_id": "waifu_m_001", "name": "Mythic Nezuko", "rarity": "MYTHIC", "image_url": "https://i.imgur.com/placeholder10.jpg", "series": "Demon Slayer"},
        {"card_id": "waifu_m_002", "name": "Mythic Miku", "rarity": "MYTHIC", "image_url": "https://i.imgur.com/placeholder11.jpg", "series": "Vocaloid"},
        {"card_id": "waifu_m_003", "name": "Mythic Mikasa", "rarity": "MYTHIC", "image_url": "https://i.imgur.com/placeholder12.jpg", "series": "Attack on Titan"},
        {"card_id": "waifu_m_004", "name": "Mythic Power", "rarity": "MYTHIC", "image_url": "https://i.imgur.com/placeholder13.jpg", "series": "Chainsaw Man"},
        {"card_id": "waifu_m_005", "name": "Mythic Mai", "rarity": "MYTHIC", "image_url": "https://i.imgur.com/placeholder14.jpg", "series": "Bunny Girl Senpai"},
        
        # LEGENDARY
        {"card_id": "waifu_leg_001", "name": "Legendary Hinata", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder15.jpg", "series": "Naruto"},
        {"card_id": "waifu_leg_002", "name": "Legendary Tsunade", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder16.jpg", "series": "Naruto"},
        {"card_id": "waifu_leg_003", "name": "Legendary Erza", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder17.jpg", "series": "Fairy Tail"},
        {"card_id": "waifu_leg_004", "name": "Legendary Rias", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder18.jpg", "series": "High School DxD"},
        {"card_id": "waifu_leg_005", "name": "Legendary Raphtalia", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder19.jpg", "series": "Shield Hero"},
        {"card_id": "waifu_leg_006", "name": "Legendary Aqua", "rarity": "LEGENDARY", "image_url": "https://i.imgur.com/placeholder20.jpg", "series": "KonoSuba"},
        
        # EPIC
        {"card_id": "waifu_e_001", "name": "Epic Sakura", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder21.jpg", "series": "Naruto"},
        {"card_id": "waifu_e_002", "name": "Epic Ino", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder22.jpg", "series": "Naruto"},
        {"card_id": "waifu_e_003", "name": "Epic Tifa", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder23.jpg", "series": "Final Fantasy"},
        {"card_id": "waifu_e_004", "name": "Epic Nami", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder24.jpg", "series": "One Piece"},
        {"card_id": "waifu_e_005", "name": "Epic Robin", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder25.jpg", "series": "One Piece"},
        {"card_id": "waifu_e_006", "name": "Epic Levy", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder26.jpg", "series": "Fairy Tail"},
        {"card_id": "waifu_e_007", "name": "Epic Winry", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder27.jpg", "series": "Fullmetal Alchemist"},
        {"card_id": "waifu_e_008", "name": "Epic Ochako", "rarity": "EPIC", "image_url": "https://i.imgur.com/placeholder28.jpg", "series": "My Hero Academia"},
        
        # RARE
        {"card_id": "waifu_ra_001", "name": "Rare Momo", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder29.jpg", "series": "My Hero Academia"},
        {"card_id": "waifu_ra_002", "name": "Rare Tsuyu", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder30.jpg", "series": "My Hero Academia"},
        {"card_id": "waifu_ra_003", "name": "Rare Marin", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder31.jpg", "series": "My Dress-Up Darling"},
        {"card_id": "waifu_ra_004", "name": "Rare Chika", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder32.jpg", "series": "Kaguya-sama"},
        {"card_id": "waifu_ra_005", "name": "Rare Kaguya", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder33.jpg", "series": "Kaguya-sama"},
        {"card_id": "waifu_ra_006", "name": "Rare Shinobu", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder34.jpg", "series": "Demon Slayer"},
        {"card_id": "waifu_ra_007", "name": "Rare Kanao", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder35.jpg", "series": "Demon Slayer"},
        {"card_id": "waifu_ra_008", "name": "Rare Mitsuri", "rarity": "RARE", "image_url": "https://i.imgur.com/placeholder36.jpg", "series": "Demon Slayer"},
        
        # UNCOMMON
        {"card_id": "waifu_u_001", "name": "Uncommon Yui", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder37.jpg", "series": "K-On!"},
        {"card_id": "waifu_u_002", "name": "Uncommon Mio", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder38.jpg", "series": "K-On!"},
        {"card_id": "waifu_u_003", "name": "Uncommon Ritsu", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder39.jpg", "series": "K-On!"},
        {"card_id": "waifu_u_004", "name": "Uncommon Azusa", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder40.jpg", "series": "K-On!"},
        {"card_id": "waifu_u_005", "name": "Uncommon Mugi", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder41.jpg", "series": "K-On!"},
        {"card_id": "waifu_u_006", "name": "Uncommon Tohru", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder42.jpg", "series": "Dragon Maid"},
        {"card_id": "waifu_u_007", "name": "Uncommon Kanna", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder43.jpg", "series": "Dragon Maid"},
        {"card_id": "waifu_u_008", "name": "Uncommon Lucoa", "rarity": "UNCOMMON", "image_url": "https://i.imgur.com/placeholder44.jpg", "series": "Dragon Maid"},
        
        # COMMON
        {"card_id": "waifu_c_001", "name": "Common School Girl A", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder45.jpg", "series": "Generic"},
        {"card_id": "waifu_c_002", "name": "Common School Girl B", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder46.jpg", "series": "Generic"},
        {"card_id": "waifu_c_003", "name": "Common School Girl C", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder47.jpg", "series": "Generic"},
        {"card_id": "waifu_c_004", "name": "Common Maid A", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder48.jpg", "series": "Generic"},
        {"card_id": "waifu_c_005", "name": "Common Maid B", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder49.jpg", "series": "Generic"},
        {"card_id": "waifu_c_006", "name": "Common Witch A", "rarity": "COMMON", "image_url": "https://i.imgur.com/placeholder50.jpg", "series": "Generic"}
    ]
    
    # Insert all cards into master collection
    for card in master_waifu_cards:
        card["created_at"] = datetime.utcnow()
        master_cards.insert_one(card)
    
    print(f"Initialized {len(master_waifu_cards)} waifu cards in master collection!")

def get_random_price_for_rarity(rarity):
    """Get a random price within the range for a given rarity"""
    if rarity in RARITY_PRICING:
        min_price, max_price = RARITY_PRICING[rarity]
        return random.randint(min_price, max_price)
    return 1  # Default fallback

def refresh_daily_shop(shop_size=9):
    """Refresh the daily shop with random cards and pricing"""
    # Clear existing shop
    default_shop.delete_many({})
    
    # Get all available cards from master collection
    all_cards = list(master_cards.find())
    if not all_cards:
        initialize_master_cards()
        all_cards = list(master_cards.find())
    
    # Rarity weights for shop selection (higher weight = more likely to appear)
    rarity_weights = {
        "COMMON": 35,
        "UNCOMMON": 25, 
        "RARE": 20,
        "EPIC": 10,
        "LEGENDARY": 5,
        "MYTHIC": 3,
        "RETRO": 1.5,
        "ZENITH": 0.4,
        "LIMITED EDITION": 0.1
    }
    
    # Select random cards for shop with weighted rarity
    selected_cards = []
    
    for _ in range(shop_size):
        # Select rarity based on weights
        rarities = list(rarity_weights.keys())
        weights = list(rarity_weights.values())
        selected_rarity = random.choices(rarities, weights=weights)[0]
        
        # Get cards of selected rarity
        rarity_cards = [card for card in all_cards if card["rarity"] == selected_rarity]
        
        if rarity_cards:
            selected_card = random.choice(rarity_cards)
            # Create shop item with random pricing
            shop_item = {
                "card_id": selected_card["card_id"],
                "name": selected_card["name"],
                "rarity": selected_card["rarity"],
                "price": get_random_price_for_rarity(selected_card["rarity"]),
                "image_url": selected_card["image_url"],
                "series": selected_card.get("series", "Unknown"),
                "date_added": datetime.utcnow()
            }
            selected_cards.append(shop_item)
    
    # Insert selected cards into shop
    if selected_cards:
        default_shop.insert_many(selected_cards)
        print(f"Daily shop refreshed with {len(selected_cards)} new cards!")
    
    return selected_cards

def initialize_default_shop():
    """Initialize default shop by refreshing with random cards"""
    # First make sure master cards exist
    if master_cards.count_documents({}) == 0:
        initialize_master_cards()
    
    # Then refresh the shop
    refresh_daily_shop()

def get_default_shop_items():
    """Get all items in default shop"""
    return list(default_shop.find())

def buy_from_default_shop(user_id, card_id):
    """Buy a card from default shop"""
    card = default_shop.find_one({"card_id": card_id})
    if not card:
        return False, "Card not found"
    
    user = get_user(user_id)
    if not user or user["wish_balance"] < card["price"]:
        return False, "Insufficient wishes"
    
    # Deduct wishes
    users.update_one({"user_id": user_id}, {"$inc": {"wish_balance": -card["price"]}})
    
    # Add card to user's collection
    add_card_to_user(user_id, card_id, card["name"], card["rarity"])
    
    # Record transaction
    record_transaction(user_id, "shop_purchase", -card["price"], f"Bought {card['name']} from shop")
    
    return True, card

def create_p2p_listing(user_id, card_id, price):
    """Create a P2P marketplace listing"""
    # Check if user owns the card
    if not user_owns_card(user_id, card_id):
        return None, "You don't own this card"
    
    # Check if card is already listed
    existing_listing = p2p_listings.find_one({
        "seller_id": user_id,
        "card_id": card_id,
        "is_active": True
    })
    if existing_listing:
        return None, "Card is already listed"
    
    listing = {
        "seller_id": user_id,
        "card_id": card_id,
        "price": price,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    result = p2p_listings.insert_one(listing)
    return str(result.inserted_id), "Listing created successfully"

def get_p2p_listings():
    """Get all active P2P listings"""
    return list(p2p_listings.find({"is_active": True}))

def get_user_listings(user_id):
    """Get all listings by a specific user"""
    return list(p2p_listings.find({"seller_id": user_id, "is_active": True}))

def buy_from_p2p(buyer_id, listing_id):
    """Buy a card from P2P marketplace"""
    listing = p2p_listings.find_one({"_id": listing_id, "is_active": True})
    if not listing:
        return False, "Listing not found"
    
    buyer = get_user(buyer_id)
    if not buyer or buyer["wish_balance"] < listing["price"]:
        return False, "Insufficient wishes"
    
    if buyer_id == listing["seller_id"]:
        return False, "Cannot buy your own listing"
    
    # Get card details
    seller_card = user_cards.find_one({
        "user_id": listing["seller_id"],
        "card_id": listing["card_id"]
    })
    if not seller_card:
        return False, "Seller no longer owns this card"
    
    # Transfer wishes
    users.update_one({"user_id": buyer_id}, {"$inc": {"wish_balance": -listing["price"]}})
    users.update_one({"user_id": listing["seller_id"]}, {"$inc": {"wish_balance": listing["price"]}})
    
    # Transfer card ownership
    transfer_card(listing["seller_id"], buyer_id, listing["card_id"])
    
    # Deactivate listing
    p2p_listings.update_one({"_id": listing_id}, {"$set": {"is_active": False}})
    
    # Record transactions
    record_transaction(buyer_id, "p2p_purchase", -listing["price"], f"Bought {listing['card_id']} from P2P")
    record_transaction(listing["seller_id"], "p2p_sale", listing["price"], f"Sold {listing['card_id']} on P2P")
    
    return True, listing

def remove_p2p_listing(user_id, listing_id):
    """Remove a P2P listing"""
    result = p2p_listings.update_one(
        {"_id": listing_id, "seller_id": user_id},
        {"$set": {"is_active": False}}
    )
    return result.modified_count > 0

def update_p2p_listing_price(user_id, listing_id, new_price):
    """Update the price of a P2P listing"""
    result = p2p_listings.update_one(
        {"_id": listing_id, "seller_id": user_id, "is_active": True},
        {"$set": {"price": new_price}}
    )
    return result.modified_count > 0

# Card ownership management functions
def add_card_to_user(user_id, card_id, card_name=None, rarity=None):
    """Add a card to user's collection"""
    card_data = {
        "user_id": user_id,
        "card_id": card_id,
        "card_name": card_name,
        "rarity": rarity,
        "obtained_at": datetime.utcnow()
    }
    user_cards.insert_one(card_data)

def user_owns_card(user_id, card_id):
    """Check if user owns a specific card"""
    return user_cards.find_one({"user_id": user_id, "card_id": card_id}) is not None

def transfer_card(from_user_id, to_user_id, card_id):
    """Transfer a card from one user to another"""
    # Remove from seller
    card = user_cards.find_one({"user_id": from_user_id, "card_id": card_id})
    if not card:
        return False
    
    user_cards.delete_one({"user_id": from_user_id, "card_id": card_id})
    
    # Add to buyer
    add_card_to_user(to_user_id, card_id, card.get("card_name"), card.get("rarity"))
    return True

def get_user_cards(user_id):
    """Get all cards owned by a user"""
    return list(user_cards.find({"user_id": user_id}))

def get_user_card_count(user_id, card_id):
    """Get the count of a specific card owned by user"""
    return user_cards.count_documents({"user_id": user_id, "card_id": card_id})

# Rarity styling functions
def get_rarity_emoji(rarity):
    """Get emoji for rarity level"""
    rarity_emojis = {
        "LIMITED EDITION": "🌟💎🌟",
        "ZENITH": "⚡👑⚡", 
        "RETRO": "🎮✨🎮",
        "MYTHIC": "🔥💫🔥",
        "LEGENDARY": "👑💜👑",
        "EPIC": "⚔️💙⚔️",
        "RARE": "💚✨💚",
        "UNCOMMON": "🔸💛🔸",
        "COMMON": "⚪🤍⚪"
    }
    return rarity_emojis.get(rarity, "⭐")

def get_rarity_color_text(rarity):
    """Get styled text for rarity (HTML format)"""
    rarity_styles = {
        "LIMITED EDITION": "🌟 <b>ULTRA RARE EDITION</b> 🌟",
        "ZENITH": "⚡ <b>APEX TIER</b> ⚡",
        "RETRO": "🎮 <b>CLASSIC COLLECTION</b> 🎮", 
        "MYTHIC": "🔥 <b>LEGENDARY STATUS</b> 🔥",
        "LEGENDARY": "👑 <b>ROYAL TIER</b> 👑",
        "EPIC": "⚔️ <b>HEROIC GRADE</b> ⚔️",
        "RARE": "💚 <b>PREMIUM QUALITY</b> 💚",
        "UNCOMMON": "🔸 <b>SPECIAL EDITION</b> 🔸",
        "COMMON": "⚪ <b>STANDARD GRADE</b> ⚪"
    }
    return rarity_styles.get(rarity, "⭐ <b>SPECIAL CARD</b> ⭐")