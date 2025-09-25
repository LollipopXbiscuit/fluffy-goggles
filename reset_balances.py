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
    print("🔄 WARNING: This will reset ALL user balances to 0!")
    
    if users is None:
        print("❌ Database not connected. Please set MONGODB_URL environment variable.")
        return
    
    # Require confirmation
    confirm = os.getenv("CONFIRM_RESET", "")
    if confirm.lower() != "yes":
        print("❌ Operation cancelled. Set CONFIRM_RESET=yes environment variable to proceed.")
        print("   Example: CONFIRM_RESET=yes python reset_balances.py")
        return
    
    # Reset all user balances to 0
    success = reset_all_vaults()
    
    if success:
        print("✅ Successfully reset all user balances to 0")
    else:
        print("❌ Failed to reset user balances")

if __name__ == "__main__":
    main()