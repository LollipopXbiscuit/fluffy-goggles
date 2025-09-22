# Overview

TelegramStarsBot is a Telegram bot that enables users to purchase digital images using Telegram Stars (XTR), Telegram's internal currency system. The bot demonstrates integration with Telegram's payment system, providing a simple e-commerce experience within the Telegram platform. Users can browse, purchase, and receive digital content directly through the bot interface.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **pyTelegramBotAPI**: Core bot framework handling Telegram API interactions, message processing, and callback management
- **Event-driven architecture**: Uses decorators for command and callback handling with separate handlers for different user interactions

## Database Layer
- **SQLite**: Lightweight local database for payment tracking and user transaction history
- **Simple schema**: Stores user payments with user_id, payment_id, amount, and currency fields
- **Connection management**: Uses context managers for proper database connection handling

## Payment System
- **Telegram Stars integration**: Leverages Telegram's native XTR currency system for seamless in-app purchases
- **Invoice-based payments**: Creates payment invoices with labeled prices and handles successful payment callbacks
- **Payment tracking**: Records all successful transactions for audit and user management

## Configuration Management
- **Environment-based config**: Uses python-dotenv for secure token and database configuration management
- **Graceful error handling**: Validates required environment variables with clear error messaging for missing configuration

## User Interface
- **Inline keyboards**: Custom keyboard layouts for purchase flow and user interactions
- **Command handlers**: Standard Telegram bot commands (/start, /paysupport) for user navigation
- **Callback-driven flow**: Button-based interaction model for improved user experience

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