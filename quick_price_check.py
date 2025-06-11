#!/usr/bin/env python3
"""
Quick Price Anomaly Checker for ROFR Data

This script performs a focused analysis to find the most obvious price anomalies
in the ROFR CSV data, with clear explanations of what constitutes abnormal pricing.
"""

import pandas as pd
import numpy as np
import argparse
import glob
import os

def load_latest_csv(data_dir="data"):
    """Load the most recent CSV file from the data directory."""
    csv_files = glob.glob(os.path.join(data_dir, "rofr_data_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    latest_file = max(csv_files, key=os.path.getctime)
    print(f"Analyzing: {latest_file}")
    return pd.read_csv(latest_file)

def analyze_extreme_prices(df):
    """Find obviously abnormal prices."""
    print("\n=== EXTREME PRICE ANALYSIS ===")
    
    # Very obvious outliers
    extremely_high = df[df['price_per_point'] > 500]
    extremely_low = df[df['price_per_point'] < 25]
    
    print(f"Extremely high prices (>$500/point): {len(extremely_high)}")
    if len(extremely_high) > 0:
        print("These are likely data entry errors or typos:")
        for _, row in extremely_high.iterrows():
            print(f"  {row['username']}: ${row['price_per_point']}/point for {row['points']} {row['resort']} points")
            print(f"    Raw entry: {row['raw_entry']}")
    
    print(f"\nExtremely low prices (<$25/point): {len(extremely_low)}")
    if len(extremely_low) > 0:
        print("These are likely data entry errors or very old contracts:")
        for _, row in extremely_low.iterrows():
            print(f"  {row['username']}: ${row['price_per_point']}/point for {row['points']} {row['resort']} points ({row['sent_date']})")

def check_data_parsing_errors(df):
    """Check for obvious data parsing issues."""
    print("\n=== DATA PARSING ISSUES ===")
    
    # Look for cases where price_per_point might be confused with total_cost
    suspicious = df[df['price_per_point'] > 1000]
    
    for _, row in suspicious.iterrows():
        expected_total = row['price_per_point'] * row['points']
        actual_total = row['total_cost'] if pd.notna(row['total_cost']) else 0
        
        # Check if price_per_point looks like it should be total_cost
        if pd.notna(row['total_cost']) and abs(row['price_per_point'] - row['total_cost']) < 100:
            print(f"PARSING ERROR: {row['username']} - price_per_point (${row['price_per_point']}) equals total_cost")
            print(f"  Likely actual price per point: ${row['total_cost'] / row['points']:.2f}")
            print(f"  Raw: {row['raw_entry']}")
        elif row['price_per_point'] / row['points'] > 1 and row['price_per_point'] / row['points'] < 300:
            print(f"POSSIBLE ERROR: {row['username']} - price_per_point might be total_cost")
            print(f"  If corrected: ${row['price_per_point'] / row['points']:.2f} per point")
            print(f"  Raw: {row['raw_entry']}")

def analyze_by_resort_and_year(df):
    """Analyze price ranges by resort and identify outliers within each resort."""
    print("\n=== RESORT-SPECIFIC ANALYSIS ===")
    
    # Get recent data (last 3 years) for better comparison
    df['sent_date'] = pd.to_datetime(df['sent_date'])
    recent_cutoff = df['sent_date'].max() - pd.DateOffset(years=3)
    recent_df = df[df['sent_date'] >= recent_cutoff]
    
    resort_stats = recent_df.groupby('resort')['price_per_point'].agg([
        'count', 'min', 'max', 'mean', 'median'
    ]).round(2)
    
    # Only show resorts with reasonable sample sizes
    resort_stats = resort_stats[resort_stats['count'] >= 20]
    resort_stats = resort_stats.sort_values('median', ascending=False)
    
    print("Recent price ranges by resort (last 3 years, 20+ samples):")
    print(resort_stats)
    
    print("\nOutliers within each resort:")
    for resort in resort_stats.index:
        resort_data = recent_df[recent_df['resort'] == resort]
        q25 = resort_data['price_per_point'].quantile(0.25)
        q75 = resort_data['price_per_point'].quantile(0.75)
        iqr = q75 - q25
        
        outliers = resort_data[
            (resort_data['price_per_point'] < q25 - 2*iqr) | 
            (resort_data['price_per_point'] > q75 + 2*iqr)
        ]
        
        if len(outliers) > 0:
            print(f"\n{resort} outliers (normal range: ${q25:.0f}-${q75:.0f}):")
            for _, row in outliers.iterrows():
                print(f"  {row['username']}: ${row['price_per_point']}/point ({row['sent_date'].strftime('%Y-%m-%d')})")

def check_calculation_consistency(df):
    """Check if price_per_point * points = total_cost."""
    print("\n=== CALCULATION CONSISTENCY CHECK ===")
    
    # Filter out entries without total_cost
    calc_df = df.dropna(subset=['total_cost'])
    
    # Calculate expected total
    calc_df = calc_df.copy()
    calc_df['expected_total'] = calc_df['price_per_point'] * calc_df['points']
    calc_df['difference'] = abs(calc_df['total_cost'] - calc_df['expected_total'])
    
    # Allow small differences for rounding/fees
    tolerance = 100
    inconsistent = calc_df[calc_df['difference'] > tolerance]
    
    print(f"Entries with calculation inconsistencies (>${tolerance}+ difference): {len(inconsistent)}")
    print(f"Percentage of entries with issues: {len(inconsistent)/len(calc_df)*100:.1f}%")
    
    if len(inconsistent) > 0:
        print("\nWorst inconsistencies:")
        worst = inconsistent.nlargest(10, 'difference')
        for _, row in worst.iterrows():
            print(f"  {row['username']}: ${row['price_per_point']}/point × {row['points']} = ${row['expected_total']:.0f}, but total_cost = ${row['total_cost']:.0f}")
            print(f"    Difference: ${row['difference']:.0f}")

def find_likely_typos(df):
    """Find entries that are likely typos based on digit patterns."""
    print("\n=== LIKELY TYPOS ===")
    
    # Look for prices that might have extra/missing digits
    for _, row in df.iterrows():
        price = row['price_per_point']
        
        # Check if removing a digit makes it reasonable
        price_str = str(int(price))
        
        if price > 1000:  # Suspiciously high
            # Try removing each digit to see if it becomes reasonable
            for i in range(len(price_str)):
                test_price = float(price_str[:i] + price_str[i+1:]) if len(price_str) > 1 else 0
                if 50 <= test_price <= 300:  # Reasonable DVC price range
                    print(f"POSSIBLE TYPO: {row['username']} - ${price} might be ${test_price}")
                    print(f"  (Remove digit at position {i+1})")
                    break
        
        elif price < 50 and price > 0:  # Suspiciously low but not zero
            # Try adding a digit
            for digit in '123456789':
                for pos in range(len(price_str) + 1):
                    test_price = float(price_str[:pos] + digit + price_str[pos:])
                    if 80 <= test_price <= 200:  # Common DVC price range
                        print(f"POSSIBLE TYPO: {row['username']} - ${price} might be ${test_price}")
                        print(f"  (Add '{digit}' at position {pos+1})")
                        break

def main():
    parser = argparse.ArgumentParser(description='Quick price anomaly check for ROFR data')
    parser.add_argument('--csv', help='Path to specific CSV file (optional)')
    parser.add_argument('--export', action='store_true', help='Export anomalies to CSV')
    
    args = parser.parse_args()
    
    try:
        # Load data
        if args.csv:
            df = pd.read_csv(args.csv)
            print(f"Loading: {args.csv}")
        else:
            df = load_latest_csv()
        
        print(f"Total records: {len(df)}")
        
        # Clean data
        df = df[df['price_per_point'].notna() & (df['price_per_point'] > 0)]
        print(f"Valid price records: {len(df)}")
        
        # Basic stats
        print(f"\nPrice range: ${df['price_per_point'].min():.2f} - ${df['price_per_point'].max():.2f}")
        print(f"Median price: ${df['price_per_point'].median():.2f}")
        print(f"Mean price: ${df['price_per_point'].mean():.2f}")
        
        # Run analyses
        analyze_extreme_prices(df)
        check_data_parsing_errors(df)
        check_calculation_consistency(df)
        analyze_by_resort_and_year(df)
        find_likely_typos(df)
        
        # Export if requested
        if args.export:
            # Export the most obvious problems
            extreme_outliers = df[
                (df['price_per_point'] > 500) | 
                (df['price_per_point'] < 25)
            ]
            
            if len(extreme_outliers) > 0:
                extreme_outliers.to_csv('extreme_price_outliers.csv', index=False)
                print(f"\nExtreme outliers exported to: extreme_price_outliers.csv")
            else:
                print("\nNo extreme outliers to export")
        
        print(f"\n=== SUMMARY ===")
        print(f"This analysis found several categories of price anomalies:")
        print(f"1. Extreme prices (>$500 or <$25) - likely data entry errors")
        print(f"2. Parsing errors - where price_per_point may be confused with total_cost")
        print(f"3. Calculation inconsistencies - where the math doesn't add up")
        print(f"4. Resort-specific outliers - prices unusual for that resort")
        print(f"5. Likely typos - prices that could be fixed by adding/removing a digit")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())