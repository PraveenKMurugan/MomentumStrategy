"""
Fix Database Schema & Create Strategy Files
Run this script to:
1. Add index_membership column to stocks table
2. Update index_membership with appropriate values
3. Create all preset strategy JSON files
"""

import sqlite3
import json
import os
from datetime import datetime

def fix_database_schema(db_path='indian_stocks.db'):
    """
    Fix database schema by adding index_membership column
    and populating it with appropriate values
    """
    print("="*80)
    print("FIXING DATABASE SCHEMA")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Step 1: Check if column exists
    cursor.execute("PRAGMA table_info(stocks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'index_membership' not in columns:
        print("\n1. Adding index_membership column...")
        
        try:
            cursor.execute('''
                ALTER TABLE stocks 
                ADD COLUMN index_membership TEXT DEFAULT 'UNKNOWN'
            ''')
            conn.commit()
            print("   ✓ Column added successfully")
        except Exception as e:
            print(f"   Note: {e}")
    else:
        print("\n1. index_membership column already exists")
    
    # Step 2: Add is_active column if missing
    if 'is_active' not in columns:
        print("\n2. Adding is_active column...")
        try:
            cursor.execute('''
                ALTER TABLE stocks 
                ADD COLUMN is_active INTEGER DEFAULT 1
            ''')
            conn.commit()
            print("   ✓ Column added successfully")
        except Exception as e:
            print(f"   Note: {e}")
    
    # Step 3: Update index_membership based on existing data
    print("\n3. Updating index_membership values...")
    
    # Get all stocks
    cursor.execute("SELECT symbol FROM stocks")
    all_symbols = [row[0] for row in cursor.fetchall()]
    
    print(f"   Found {len(all_symbols)} stocks in database")
    
    # Define index memberships
    # These are examples - you should update with actual current constituents
    
    # Nifty 50 (Top 50 by market cap)
    nifty_50 = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS',
        'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'HCLTECH.NS',
        'BAJFINANCE.NS', 'TITAN.NS', 'WIPRO.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS',
        'SUNPHARMA.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'TATAMOTORS.NS',
        'TATASTEEL.NS', 'BAJAJFINSV.NS', 'M&M.NS', 'HDFCLIFE.NS', 'TECHM.NS',
        'COALINDIA.NS', 'INDUSINDBK.NS', 'ADANIPORTS.NS', 'CIPLA.NS', 'DIVISLAB.NS',
        'JSWSTEEL.NS', 'APOLLOHOSP.NS', 'DRREDDY.NS', 'BRITANNIA.NS', 'EICHERMOT.NS',
        'HEROMOTOCO.NS', 'HINDALCO.NS', 'GRASIM.NS', 'TATACONSUM.NS', 'BAJAJ-AUTO.NS',
        'SBILIFE.NS', 'BPCL.NS', 'UPL.NS', 'VEDL.NS', 'ADANIENT.NS'
    ]
    
    # Update Nifty 50
    updated_nifty50 = 0
    for symbol in nifty_50:
        if symbol in all_symbols:
            cursor.execute('''
                UPDATE stocks 
                SET index_membership = 'NIFTY50,NIFTY500,ALL'
                WHERE symbol = ?
            ''', [symbol])
            updated_nifty50 += 1
    
    print(f"   ✓ Updated {updated_nifty50} Nifty 50 stocks")
    
    # Update all others as NIFTY500 or ALL
    cursor.execute('''
        UPDATE stocks 
        SET index_membership = 'NIFTY500,ALL'
        WHERE index_membership = 'UNKNOWN' OR index_membership IS NULL
    ''')
    
    updated_others = cursor.rowcount
    print(f"   ✓ Updated {updated_others} other stocks as NIFTY500")
    
    # Step 4: Update based on symbol patterns (if available)
    # Midcap pattern
    cursor.execute('''
        UPDATE stocks 
        SET index_membership = index_membership || ',NIFTY_MIDCAP'
        WHERE symbol IN (
            SELECT symbol FROM stocks 
            WHERE index_membership LIKE '%NIFTY500%'
            AND symbol NOT IN (
                SELECT symbol FROM stocks WHERE index_membership LIKE '%NIFTY50%'
            )
            LIMIT 150
        )
    ''')
    print(f"   ✓ Tagged {cursor.rowcount} stocks as NIFTY_MIDCAP")
    
    conn.commit()
    
    # Step 5: Verify updates
    print("\n4. Verification:")
    cursor.execute("SELECT index_membership, COUNT(*) FROM stocks GROUP BY index_membership")
    results = cursor.fetchall()
    
    for membership, count in results:
        print(f"   {membership}: {count} stocks")
    
    conn.close()
    
    print("\n✓ Database schema fixed successfully!")
    print("="*80)

def create_strategy_files():
    """
    Create all preset strategy JSON files
    """
    print("\n" + "="*80)
    print("CREATING STRATEGY FILES")
    print("="*80)
    
    # Create strategies directory if it doesn't exist
    os.makedirs('config/strategies', exist_ok=True)
    
    # Strategy 1: Classic Momentum (12M-1M)
    classic_momentum = {
        "config_name": "Classic_Momentum",
        "universe": "NIFTY500",
        "custom_symbols": None,
        "performance_periods": {
            "12M": {
                "days": 252,
                "weight": 1.0
            },
            "1M": {
                "days": 21,
                "weight": -1.0
            }
        },
        "volatility_periods": {
            "6M_vol": 126
        },
        "momentum_weights": {
            "12M": 1.0,
            "1M": -1.0
        },
        "filters": {
            "volume": {
                "min_value": 100000
            },
            "volatility": {
                "max_value": 60
            }
        }
    }
    
    # Strategy 2: Balanced Momentum (12M, 6M, 3M)
    balanced_momentum = {
        "config_name": "Balanced_Momentum",
        "universe": "NIFTY500",
        "custom_symbols": None,
        "performance_periods": {
            "12M": {
                "days": 252,
                "weight": 0.5
            },
            "6M": {
                "days": 126,
                "weight": 0.3
            },
            "3M": {
                "days": 63,
                "weight": 0.2
            }
        },
        "volatility_periods": {
            "6M_vol": 126
        },
        "momentum_weights": {
            "12M": 0.5,
            "6M": 0.3,
            "3M": 0.2
        },
        "filters": {
            "volume": {
                "min_value": 100000
            },
            "volatility": {
                "max_value": 60
            },
            "momentum": {
                "min_value": 10
            }
        }
    }
    
    # Strategy 3: Short Term Momentum (6M + 3M)
    short_term_momentum = {
        "config_name": "Short_Term_Momentum",
        "universe": "NIFTY500",
        "custom_symbols": None,
        "performance_periods": {
            "6M": {
                "days": 126,
                "weight": 0.6
            },
            "3M": {
                "days": 63,
                "weight": 0.4
            }
        },
        "volatility_periods": {
            "3M_vol": 63
        },
        "momentum_weights": {
            "6M": 0.6,
            "3M": 0.4
        },
        "filters": {
            "volume": {
                "min_value": 100000
            },
            "volatility": {
                "max_value": 50
            }
        }
    }
    
    # Strategy 4: Conservative (Low volatility blue chips)
    conservative = {
        "config_name": "Conservative",
        "universe": "NIFTY50",
        "custom_symbols": None,
        "performance_periods": {
            "12M": {
                "days": 252,
                "weight": 0.6
            },
            "6M": {
                "days": 126,
                "weight": 0.4
            }
        },
        "volatility_periods": {
            "6M_vol": 126
        },
        "momentum_weights": {
            "12M": 0.6,
            "6M": 0.4
        },
        "filters": {
            "volume": {
                "min_value": 500000
            },
            "volatility": {
                "max_value": 40
            },
            "momentum": {
                "min_value": 5
            }
        }
    }
    
    # Strategy 5: Aggressive (High momentum, higher volatility OK)
    aggressive = {
        "config_name": "Aggressive",
        "universe": "NIFTY500",
        "custom_symbols": None,
        "performance_periods": {
            "6M": {
                "days": 126,
                "weight": 0.7
            },
            "3M": {
                "days": 63,
                "weight": 0.3
            }
        },
        "volatility_periods": {
            "3M_vol": 63
        },
        "momentum_weights": {
            "6M": 0.7,
            "3M": 0.3
        },
        "filters": {
            "volume": {
                "min_value": 50000
            },
            "volatility": {
                "max_value": 80
            },
            "momentum": {
                "min_value": 15
            }
        }
    }
    
    # Save all strategies
    strategies = {
        'classic_momentum.json': classic_momentum,
        'balanced_momentum.json': balanced_momentum,
        'short_term_momentum.json': short_term_momentum,
        'conservative.json': conservative,
        'aggressive.json': aggressive
    }
    
    print("\nCreating strategy files:")
    for filename, strategy in strategies.items():
        filepath = os.path.join('config/strategies', filename)
        with open(filepath, 'w', encoding="utf-8") as f:
            json.dump(strategy, f, indent=2)
        print(f"   ✓ Created {filepath}")
    
    # Create custom_strategies.json as a template
    custom_template = {
        "config_name": "My_Custom_Strategy",
        "description": "Template for creating custom strategies",
        "universe": "NIFTY500",
        "custom_symbols": None,
        "performance_periods": {
            "6M": {
                "days": 126,
                "weight": 0.6,
                "description": "6 month return with 60% weight"
            },
            "3M": {
                "days": 63,
                "weight": 0.4,
                "description": "3 month return with 40% weight"
            }
        },
        "volatility_periods": {
            "6M_vol": 126
        },
        "momentum_weights": {
            "6M": 0.6,
            "3M": 0.4
        },
        "filters": {
            "volume": {
                "min_value": 100000,
                "description": "Minimum daily trading volume"
            },
            "volatility": {
                "max_value": 55,
                "description": "Maximum annualized volatility %"
            },
            "momentum": {
                "min_value": 8,
                "description": "Minimum momentum score"
            }
        },
        "notes": "Modify this template to create your own strategies"
    }
    
    filepath = os.path.join('config/strategies', 'custom_strategies.json')
    with open(filepath, 'w', encoding="utf-8") as f:
        json.dump(custom_template, f, indent=2)
    print(f"   ✓ Created {filepath} (template)")
    
    print("\n✓ All strategy files created successfully!")
    print("="*80)

def create_database_update_script():
    """
    Create a script to update index_membership for existing stocks
    based on manual lists or API data
    """
    
    script_content = '''"""
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
    
    with open(csv_file, 'r') as f:
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
    
    choice = input("\\nChoose method (1/2): ")
    
    if choice == "1":
        update_from_nse_api()
    elif choice == "2":
        update_from_manual_list()
    else:
        print("Invalid choice")
'''
    
    # Save the script
    os.makedirs('scripts', exist_ok=True)
    with open('scripts/update_index_membership.py', 'w', encoding="utf-8") as f:
        f.write(script_content)
    
    print("\n✓ Created scripts/update_index_membership.py")

def verify_fixes(db_path='indian_stocks.db'):
    """
    Verify that all fixes were applied correctly
    """
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check schema
    print("\n1. Database Schema:")
    cursor.execute("PRAGMA table_info(stocks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = ['index_membership', 'is_active']
    for col in required_columns:
        status = "✓" if col in columns else "✗"
        print(f"   {status} {col}")
    
    # Check data
    print("\n2. Index Membership Distribution:")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN index_membership LIKE '%NIFTY50%' THEN 'NIFTY50'
                WHEN index_membership LIKE '%NIFTY_MIDCAP%' THEN 'NIFTY_MIDCAP'
                WHEN index_membership LIKE '%NIFTY500%' THEN 'NIFTY500'
                ELSE 'OTHER'
            END as category,
            COUNT(*) as count
        FROM stocks
        GROUP BY category
    """)
    
    for category, count in cursor.fetchall():
        print(f"   {category}: {count} stocks")
    
    # Check strategy files
    print("\n3. Strategy Files:")
    strategy_files = [
        'classic_momentum.json',
        'balanced_momentum.json',
        'short_term_momentum.json',
        'conservative.json',
        'aggressive.json',
        'custom_strategies.json'
    ]
    
    for filename in strategy_files:
        filepath = os.path.join('config/strategies', filename)
        status = "✓" if os.path.exists(filepath) else "✗"
        print(f"   {status} {filepath}")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✓ VERIFICATION COMPLETE")
    print("="*80)

def main():
    """
    Main function to run all fixes
    """
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "FIX DATABASE & CREATE STRATEGIES" + " "*26 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\nThis script will:")
    print("1. Add index_membership column to database")
    print("2. Populate index_membership with values")
    print("3. Create all preset strategy JSON files")
    print("4. Verify all fixes")
    
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    try:
        # Fix database
        fix_database_schema()
        
        # Create strategy files
        create_strategy_files()
        
        # Create update script
        create_database_update_script()
        
        # Verify
        verify_fixes()
        
        print("\n" + "="*80)
        print("✓ ALL FIXES COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        print("\nNext steps:")
        print("1. Run your analysis: python scripts/run_analysis.py")
        print("2. Or update index membership: python scripts/update_index_membership.py")
        print("3. Load strategies using:")
        print("   from src.analysis.dynamic_analyzer import StrategyConfig")
        print("   config = StrategyConfig.load('config/strategies/balanced_momentum.json')")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. Database file exists (indian_stocks.db)")
        print("2. You have write permissions")
        print("3. Database is not locked by another process")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()