import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv('MONGODB_URL')
client = MongoClient(MONGODB_URL)
db = client.telegram_bot

# Collections
users = db.users
transactions = db.transactions
default_shop = db.default_shop
p2p_listings = db.p2p_listings

def create_user(user_id, username=None):
    """Create a new user or return existing user"""
    existing_user = users.find_one({"user_id": user_id})
    if existing_user:
        return existing_user
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "wish_balance": 0,
        "last_daily_claim": None,
        "created_at": datetime.utcnow()
    }
    users.insert_one(user_data)
    return user_data

def get_user(user_id):
    """Get user by ID"""
    return users.find_one({"user_id": user_id})

def update_user_balance(user_id, amount):
    """Update user's wish balance (can be positive or negative)"""
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
    user = get_user(user_id)
    if not user:
        return False
    
    if not user["last_daily_claim"]:
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

def transfer_wishes(from_user_id, to_user_id, amount):
    """Transfer wishes between users"""
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
    return list(transactions.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))

def add_wishes_for_stars(user_id, stars_amount, conversion_rate=10):
    """Add wishes when user buys with Telegram Stars"""
    wish_amount = stars_amount * conversion_rate
    update_user_balance(user_id, wish_amount)
    record_transaction(user_id, "stars_purchase", wish_amount, f"Purchased {wish_amount} wishes with {stars_amount} stars")
    return wish_amount

def initialize_default_shop():
    """Initialize default shop with sample waifu cards"""
    # Clear existing shop
    default_shop.delete_many({})
    
    # Sample waifu cards for testing
    sample_cards = [
        {"card_id": "waifu_001", "name": "Sakura", "rarity": "Common", "price": 5, "image_url": ""},
        {"card_id": "waifu_002", "name": "Hinata", "rarity": "Rare", "price": 15, "image_url": ""},
        {"card_id": "waifu_003", "name": "Tsunade", "rarity": "Epic", "price": 30, "image_url": ""},
        {"card_id": "waifu_004", "name": "Nezuko", "rarity": "Legendary", "price": 50, "image_url": ""},
        {"card_id": "waifu_005", "name": "Zero Two", "rarity": "Mythic", "price": 100, "image_url": ""}
    ]
    
    for card in sample_cards:
        card["date_added"] = datetime.utcnow()
        default_shop.insert_one(card)

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
    
    # Record transaction
    record_transaction(user_id, "shop_purchase", -card["price"], f"Bought {card['name']} from shop")
    
    return True, card

def create_p2p_listing(user_id, card_id, price):
    """Create a P2P marketplace listing"""
    listing = {
        "seller_id": user_id,
        "card_id": card_id,
        "price": price,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    result = p2p_listings.insert_one(listing)
    return str(result.inserted_id)

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
    
    # Transfer wishes
    users.update_one({"user_id": buyer_id}, {"$inc": {"wish_balance": -listing["price"]}})
    users.update_one({"user_id": listing["seller_id"]}, {"$inc": {"wish_balance": listing["price"]}})
    
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