"""
Update Index Membership Script
Run this to update index membership from NSE or manual lists
"""

import sqlite3
import requests
from bs4 import BeautifulSoup

def update_from_nse_api(db_path='indian_stocks.db'):
    """
    Update index membership from NSE API
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # NSE API endpoints (may require session/cookies)
    indices = {
        'NIFTY 50': 'NIFTY50',
        'NIFTY 500': 'NIFTY500',
        'NIFTY MIDCAP 100': 'NIFTY_MIDCAP',
        'NIFTY SMALLCAP 100': 'NIFTY_SMALLCAP'
    }
    
    print("Updating from NSE API...")
    
    # Note: NSE API requires proper session handling
    # This is a simplified version
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Get homepage for cookies
    session.get('https://www.nseindia.com')
    
    for index_name, index_tag in indices.items():
        try:
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_name.replace(' ', '%20')}"
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('data', []):
                    symbol = item.get('symbol')
                    if symbol:
                        symbol_ns = symbol + '.NS'
                        
                        # Update membership
                        cursor.execute("""
                            UPDATE stocks 
                            SET index_membership = CASE 
                                WHEN index_membership LIKE ? THEN index_membership
                                ELSE index_membership || ',' || ?
                            END
                            WHERE symbol = ?
                        """, [f'%{index_tag}%', index_tag, symbol_ns])
                
                print(f"✓ Updated {index_name}")
        
        except Exception as e:
            print(f"⚠ Could not update {index_name}: {e}")
    
    conn.commit()
    conn.close()
    print("✓ Update complete!")

def update_from_manual_list(db_path='indian_stocks.db'):
    """
    Update from manual CSV file
    
    Create a CSV file: config/index_constituents.csv
    Format: symbol,index_membership
    Example:
    RELIANCE.NS,NIFTY50;NIFTY500
    TCS.NS,NIFTY50;NIFTY500
    """
    import csv
    import os
    
    csv_file = 'config/index_constituents.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        print("Create this file with format: symbol,index_membership")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(csv_file, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            symbol = row['symbol']
            membership = row['index_membership'].replace(';', ',')
            
            cursor.execute("""
                UPDATE stocks 
                SET index_membership = ?
                WHERE symbol = ?
            """, [membership, symbol])
            
            count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✓ Updated {count} stocks from CSV")

if __name__ == "__main__":
    import sys
    
    print("Index Membership Update Script")
    print("="*60)
    print("1. Update from NSE API (requires internet)")
    print("2. Update from manual CSV file")
    
    choice = input("\nChoose method (1/2): ")
    
    if choice == "1":
        update_from_nse_api()
    elif choice == "2":
        update_from_manual_list()
    else:
        print("Invalid choice")
