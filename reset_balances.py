#!/usr/bin/env python3
"""
Script to reset all user balances to 0
"""
import os
from utils import reset_all_vaults, users
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🔄 Resetting all user balances...")
    
    if users is None:
        print("❌ Database not connected. Please set MONGODB_URL environment variable.")
        return
    
    # Reset all user balances to 0
    success = reset_all_vaults()
    
    if success:
        print("✅ Successfully reset all user balances to 0")
    else:
        print("❌ Failed to reset user balances")

if __name__ == "__main__":
    main()