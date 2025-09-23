# Overview

WishBot is a comprehensive Telegram bot featuring a custom currency system called "Wish" (𝓒) with integrated marketplace functionality. Users can earn, transfer, and spend wishes on waifu cards through both a daily shop and peer-to-peer marketplace. The bot includes Telegram Stars integration for purchasing wishes and connects to MongoDB for persistent data storage.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **python-telegram-bot v22**: Modern async bot framework with comprehensive Telegram API support
- **Event-driven architecture**: Command handlers, callback query handlers, and payment handlers
- **Modular structure**: Separated into main.py, utils.py, and shop.py for maintainability

## Database Layer
- **MongoDB**: Cloud database integration using user's MONGODB_URL secret
- **Collections**: users, transactions, default_shop, p2p_listings, user_cards
- **Card ownership system**: Proper tracking of user-owned cards with ownership validation
- **Transaction safety**: Prevents negative balances and validates card ownership before transfers

## Currency System
- **Custom Wish currency (𝓒)**: Internal bot currency for purchasing cards
- **Daily rewards**: 24-hour cooldown system for free wish claims
- **Transfer system**: Send wishes between users via username or user ID
- **Transaction history**: Complete audit trail of all currency movements

## Payment Integration
- **Telegram Stars (XTR)**: Native Telegram payment system for buying wishes
- **Multiple packages**: 1-50 star packages with configurable conversion rates
- **Secure processing**: Pre-checkout validation and successful payment handling

## Marketplace System
- **Daily Shop**: Curated waifu cards with rarity-based pricing
- **P2P Marketplace**: User-to-user card trading with ownership validation
- **Inventory management**: Complete card collection tracking with duplicate counting
- **Listing controls**: Create, view, and manage marketplace listings

## Security & Configuration
- **Environment secrets**: Secure BOT_TOKEN and OWNER_ID management via Replit Secrets
- **Log sanitization**: Suppressed httpx logs to prevent token exposure
- **Owner privileges**: Admin commands restricted to configured owner ID
- **Input validation**: Comprehensive parameter validation and error handling

# External Dependencies

## Telegram Bot API
- **Purpose**: Core bot functionality and message handling
- **Integration**: Direct API communication through pyTelegramBotAPI wrapper
- **Authentication**: Bot token-based authentication for secure API access

## Telegram Stars Payment System
- **Purpose**: Native payment processing within Telegram ecosystem
- **Integration**: Invoice creation and payment verification through Telegram's payment API
- **Currency**: Uses XTR (Telegram Stars) as the transaction currency

## Python Libraries
- **pyTelegramBotAPI**: Telegram bot framework for API interactions and event handling
- **python-dotenv**: Environment variable management for secure configuration loading
- **sqlite3**: Built-in Python SQLite interface for local database operations

## Environment Configuration
- **TOKEN**: Telegram Bot API token for authentication and bot identification
- **DATABASE**: SQLite database file path for payment storage and retrieval