import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
symbol = "NVDA"

# API Endpoint
url = f"https://api.marketdata.app/v1/options/chain/{symbol}/"
headers = {"Authorization": f"Token {API_KEY}"}

try:
    # Make the API request
    print(f"Fetching options chain for {symbol}...")
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    # Parse the response
    chain_data = response.json()
    
    # Convert to DataFrame
    df = pd.DataFrame(chain_data)
    
    # ===== DATA CLEANING & FILTERING =====
    # Convert expiration from timestamp to datetime
    df['expiration'] = pd.to_datetime(df['expiration'], unit='s')
    
    # Ensure IV is numeric
    df['iv'] = pd.to_numeric(df['iv'], errors='coerce')
    
    # Remove rows with bad IV or prices
    df = df[(df['iv'] > 0) & (df['bid'] > 0) & (df['ask'] > 0)]
    
    # Get current spot price safely
    if 'underlyingPrice' in df.columns and not df['underlyingPrice'].isna().all():
        spot = df['underlyingPrice'].iloc[0]
    else:
        spot = yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]

    print(f"\nSpot Price: ${spot:.2f}")
    
    # Keep only near-ATM strikes (±15% of spot)
    df = df[(df['strike'] > spot * 0.85) & (df['strike'] < spot * 1.15)]
    
    # Keep only the first 2 expiries
    nearest_exps = sorted(df['expiration'].unique())[:2]
    df = df[df['expiration'].isin(nearest_exps)]
    print(f"Using expiries: {[d.strftime('%Y-%m-%d') for d in nearest_exps]}")
    
    # Check if we have data after all filtering
    if df.empty:
        raise ValueError("No valid near-ATM options after filtering — widen strike range or check data.")
    
    # Calculate forward variance
    df['variance'] = df['iv']**2
    variance_by_exp = df.groupby('expiration')['variance'].mean()
    
    print("\nForward Implied Variance by Expiry:")
    print(variance_by_exp.to_string())
    print("\n" + "="*50)
    
    # Basic info
    print(f"\n{'='*50}")
    print(f"OPTIONS CHAIN ANALYSIS - {symbol.upper()}")
    print(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total contracts: {len(df):,}")
    
    # Split calls and puts
    calls = df[df['side'] == 'call'].copy()
    puts = df[df['side'] == 'put'].copy()
    
    print(f"Calls: {len(calls):,}, Puts: {len(puts):,}")
    
    # Calculate mid prices and spreads
    df['mid'] = (df['bid'] + df['ask']) / 2
    df['spread'] = df['ask'] - df['bid']
    df['spread_pct'] = df['spread'] / df['mid'] * 100
    
    # Display key metrics
    print("\nKey Metrics:")
    print(f"Average IV: {df['iv'].mean():.1%}")
    print(f"Widest Spread: {df['spread_pct'].max():.1f}%")
    
    # Show sample of the data
    print("\nSample Contracts:")
    display_cols = ['optionSymbol', 'side', 'strike', 'expiration', 'mid', 'iv', 'delta', 'volume', 'openInterest']
    print(df[display_cols].head().to_string(index=False))
    
    # Basic analytics
    print("\nOpen Interest by Strike:")
    oi_by_strike = df.groupby('strike')['openInterest'].sum().sort_values(ascending=False).head(5)
    print(oi_by_strike.to_string())
    
    # Calculate gamma exposure (simplified)
    if 'gamma' in df.columns and 'openInterest' in df.columns:
        df['gamma_exposure'] = df['gamma'] * df['openInterest']
        print("\nTop Gamma Exposure Strikes:")
        print(df[['strike', 'gamma_exposure']].nlargest(5, 'gamma_exposure').to_string(index=False))
    
    print("\nAnalysis complete!")
    print("="*50)
    
except requests.exceptions.RequestException as e:
    print(f"\n Error making request: {e}")
except ValueError as e:
    print(f"\nError parsing JSON response: {e}")
except KeyError as e:
    print(f"\n Missing expected data in response: {e}")
    print("\nAvailable columns in response:", list(chain_data.keys()) if 'chain_data' in locals() else 'No data received')
except Exception as e:
    print(f"\n An unexpected error occurred: {e}")
    if 'df' in locals():
        print("\nDataFrame columns:", df.columns.tolist())
