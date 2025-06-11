#!/usr/bin/env python3
"""
Script to find abnormal price per point values in ROFR CSV data.

This script analyzes the price_per_point column and identifies outliers using
multiple statistical methods including IQR, Z-score, and percentile-based detection.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import glob
import os


def load_latest_csv(data_dir="data"):
    """Load the most recent CSV file from the data directory."""
    csv_files = glob.glob(os.path.join(data_dir, "rofr_data_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    latest_file = max(csv_files, key=os.path.getctime)
    print(f"Loading data from: {latest_file}")
    return pd.read_csv(latest_file)


def calculate_basic_stats(df):
    """Calculate and display basic statistics for price per point."""
    price_stats = df['price_per_point'].describe()
    print("\n=== BASIC STATISTICS ===")
    print(price_stats)
    print(f"Skewness: {df['price_per_point'].skew():.2f}")
    print(f"Kurtosis: {df['price_per_point'].kurtosis():.2f}")
    return price_stats


def find_outliers_iqr(df, multiplier=1.5):
    """Find outliers using Interquartile Range (IQR) method."""
    Q1 = df['price_per_point'].quantile(0.25)
    Q3 = df['price_per_point'].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR
    
    outliers = df[(df['price_per_point'] < lower_bound) | 
                  (df['price_per_point'] > upper_bound)]
    
    print(f"\n=== IQR METHOD (multiplier={multiplier}) ===")
    print(f"Lower bound: ${lower_bound:.2f}")
    print(f"Upper bound: ${upper_bound:.2f}")
    print(f"Found {len(outliers)} outliers ({len(outliers)/len(df)*100:.1f}% of data)")
    
    return outliers, lower_bound, upper_bound


def find_outliers_zscore(df, threshold=3):
    """Find outliers using Z-score method."""
    mean = df['price_per_point'].mean()
    std = df['price_per_point'].std()
    z_scores = np.abs((df['price_per_point'] - mean) / std)
    outliers = df[z_scores > threshold]
    
    print(f"\n=== Z-SCORE METHOD (threshold={threshold}) ===")
    print(f"Found {len(outliers)} outliers ({len(outliers)/len(df)*100:.1f}% of data)")
    
    return outliers


def find_outliers_percentile(df, lower_percentile=1, upper_percentile=99):
    """Find outliers using percentile method."""
    lower_bound = df['price_per_point'].quantile(lower_percentile / 100)
    upper_bound = df['price_per_point'].quantile(upper_percentile / 100)
    
    outliers = df[(df['price_per_point'] < lower_bound) | 
                  (df['price_per_point'] > upper_bound)]
    
    print(f"\n=== PERCENTILE METHOD ({lower_percentile}%-{upper_percentile}%) ===")
    print(f"Lower bound: ${lower_bound:.2f}")
    print(f"Upper bound: ${upper_bound:.2f}")
    print(f"Found {len(outliers)} outliers ({len(outliers)/len(df)*100:.1f}% of data)")
    
    return outliers


def find_outliers_modified_zscore(df, threshold=3.5):
    """Find outliers using Modified Z-score method (robust to outliers)."""
    median = df['price_per_point'].median()
    mad = np.median(np.abs(df['price_per_point'] - median))
    
    # Avoid division by zero
    if mad == 0:
        mad = np.std(df['price_per_point']) * 0.6745
    
    modified_z_scores = 0.6745 * (df['price_per_point'] - median) / mad
    outliers = df[np.abs(modified_z_scores) > threshold]
    
    print(f"\n=== MODIFIED Z-SCORE METHOD (threshold={threshold}) ===")
    print(f"Found {len(outliers)} outliers ({len(outliers)/len(df)*100:.1f}% of data)")
    
    return outliers


def analyze_by_resort(df):
    """Analyze price per point distribution by resort."""
    print("\n=== ANALYSIS BY RESORT ===")
    resort_stats = df.groupby('resort')['price_per_point'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max'
    ]).round(2)
    
    # Sort by count to show most popular resorts first
    resort_stats = resort_stats.sort_values('count', ascending=False)
    print(resort_stats)
    return resort_stats


def find_resort_specific_outliers(df, method='iqr', multiplier=2.0):
    """Find outliers within each resort using specified method."""
    print(f"\n=== RESORT-SPECIFIC OUTLIERS ({method.upper()}) ===")
    all_outliers = []
    
    for resort in df['resort'].unique():
        resort_data = df[df['resort'] == resort].copy()
        
        if len(resort_data) < 10:  # Skip resorts with too few data points
            continue
            
        if method == 'iqr':
            Q1 = resort_data['price_per_point'].quantile(0.25)
            Q3 = resort_data['price_per_point'].quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR == 0:  # All values are the same
                continue
                
            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR
            
            outliers = resort_data[
                (resort_data['price_per_point'] < lower_bound) | 
                (resort_data['price_per_point'] > upper_bound)
            ]
        elif method == 'zscore':
            mean = resort_data['price_per_point'].mean()
            std = resort_data['price_per_point'].std()
            
            if std == 0:  # All values are the same
                continue
                
            z_scores = np.abs((resort_data['price_per_point'] - mean) / std)
            outliers = resort_data[z_scores > multiplier]
        
        if len(outliers) > 0:
            print(f"{resort}: {len(outliers)} outliers out of {len(resort_data)} entries")
            all_outliers.append(outliers)
    
    if all_outliers:
        return pd.concat(all_outliers, ignore_index=True)
    else:
        return pd.DataFrame()


def find_suspicious_entries(df):
    """Find potentially suspicious entries based on business logic."""
    print("\n=== SUSPICIOUS ENTRIES ===")
    suspicious = []
    
    # Very low prices (likely data entry errors)
    very_low = df[df['price_per_point'] < 10]
    if len(very_low) > 0:
        print(f"Very low prices (< $10): {len(very_low)} entries")
        suspicious.append(very_low)
    
    # Very high prices (luxury resorts or data errors)
    very_high = df[df['price_per_point'] > 300]
    if len(very_high) > 0:
        print(f"Very high prices (> $300): {len(very_high)} entries")
        suspicious.append(very_high)
    
    # Inconsistent total cost vs price per point calculation
    df_calc = df.dropna(subset=['total_cost', 'points'])
    expected_total = df_calc['price_per_point'] * df_calc['points']
    tolerance = 50  # Allow $50 difference for rounding/fees
    inconsistent = df_calc[np.abs(df_calc['total_cost'] - expected_total) > tolerance]
    
    if len(inconsistent) > 0:
        print(f"Inconsistent calculations: {len(inconsistent)} entries")
        suspicious.append(inconsistent)
    
    if suspicious:
        return pd.concat(suspicious, ignore_index=True).drop_duplicates()
    else:
        return pd.DataFrame()


def display_outliers(outliers, title, top_n=20):
    """Display outliers in a formatted table."""
    if len(outliers) == 0:
        print(f"No outliers found using {title}")
        return
    
    print(f"\n=== {title} - TOP {min(top_n, len(outliers))} OUTLIERS ===")
    display_cols = ['username', 'price_per_point', 'total_cost', 'points', 'resort', 'sent_date', 'result']
    
    # Sort by price_per_point for extreme values
    sorted_outliers = outliers.sort_values('price_per_point', ascending=False)
    
    print("HIGHEST PRICES:")
    print(sorted_outliers[display_cols].head(top_n//2).to_string(index=False))
    
    if len(sorted_outliers) > top_n//2:
        print("\nLOWEST PRICES:")
        print(sorted_outliers[display_cols].tail(top_n//2).to_string(index=False))


def create_visualizations(df, outliers_iqr, save_plots=False):
    """Create visualizations for price analysis."""
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Histogram
    axes[0, 0].hist(df['price_per_point'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    axes[0, 0].set_title('Distribution of Price Per Point')
    axes[0, 0].set_xlabel('Price Per Point ($)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Box plot
    axes[0, 1].boxplot(df['price_per_point'])
    axes[0, 1].set_title('Box Plot of Price Per Point')
    axes[0, 1].set_ylabel('Price Per Point ($)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Box plot by resort (top resorts only)
    top_resorts = df['resort'].value_counts().head(8).index
    resort_data = df[df['resort'].isin(top_resorts)]
    
    resort_prices = [resort_data[resort_data['resort'] == resort]['price_per_point'].values 
                    for resort in top_resorts]
    axes[1, 0].boxplot(resort_prices, labels=top_resorts)
    axes[1, 0].set_title('Price Per Point by Resort (Top 8)')
    axes[1, 0].set_xlabel('Resort')
    axes[1, 0].set_ylabel('Price Per Point ($)')
    axes[1, 0].tick_params(axis='x', rotation=45)
    axes[1, 0].grid(True, alpha=0.3)
    
    # Scatter plot: Price vs Points with outliers highlighted
    axes[1, 1].scatter(df['points'], df['price_per_point'], alpha=0.6, color='blue', 
                      label='Normal', s=20)
    if len(outliers_iqr) > 0:
        axes[1, 1].scatter(outliers_iqr['points'], outliers_iqr['price_per_point'], 
                          alpha=0.8, color='red', label='Outliers (IQR)', s=30)
    axes[1, 1].set_title('Price Per Point vs Contract Size')
    axes[1, 1].set_xlabel('Points')
    axes[1, 1].set_ylabel('Price Per Point ($)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_plots:
        plt.savefig('price_analysis_plots.png', dpi=300, bbox_inches='tight')
        print("\nPlots saved as 'price_analysis_plots.png'")
    
    plt.show()


def export_outliers(outliers, filename):
    """Export outliers to a CSV file."""
    if len(outliers) > 0:
        outliers.to_csv(filename, index=False)
        print(f"Outliers exported to: {filename}")
    else:
        print(f"No outliers to export for {filename}")


def main():
    parser = argparse.ArgumentParser(description='Find abnormal price per point values in ROFR data')
    parser.add_argument('--csv', help='Path to specific CSV file (optional)')
    parser.add_argument('--iqr-multiplier', type=float, default=1.5, help='IQR multiplier for outlier detection')
    parser.add_argument('--zscore-threshold', type=float, default=3.0, help='Z-score threshold for outlier detection')
    parser.add_argument('--show-plots', action='store_true', help='Display visualization plots')
    parser.add_argument('--save-plots', action='store_true', help='Save plots to file')
    parser.add_argument('--export-outliers', action='store_true', help='Export outliers to CSV')
    parser.add_argument('--top-n', type=int, default=20, help='Number of top outliers to display')
    parser.add_argument('--quick', action='store_true', help='Quick analysis (skip visualizations)')
    
    args = parser.parse_args()
    
    try:
        # Load data
        if args.csv:
            df = pd.read_csv(args.csv)
            print(f"Loading data from: {args.csv}")
        else:
            df = load_latest_csv()
        
        print(f"Loaded {len(df)} records")
        
        # Remove any invalid price data
        original_count = len(df)
        df = df[df['price_per_point'].notna() & (df['price_per_point'] > 0)]
        print(f"After filtering: {len(df)} records with valid prices ({original_count - len(df)} removed)")
        
        if len(df) == 0:
            print("No valid price data found!")
            return 1
        
        # Basic statistics
        stats_summary = calculate_basic_stats(df)
        
        # Find outliers using different methods
        outliers_iqr, lower_bound, upper_bound = find_outliers_iqr(df, args.iqr_multiplier)
        outliers_zscore = find_outliers_zscore(df, args.zscore_threshold)
        outliers_percentile = find_outliers_percentile(df, 1, 99)
        outliers_modified_zscore = find_outliers_modified_zscore(df)
        
        # Find suspicious entries
        suspicious = find_suspicious_entries(df)
        
        # Resort analysis
        resort_stats = analyze_by_resort(df)
        resort_outliers = find_resort_specific_outliers(df, 'iqr', 2.0)
        
        # Display results
        display_outliers(outliers_iqr, f"IQR METHOD (multiplier={args.iqr_multiplier})", args.top_n)
        display_outliers(outliers_zscore, f"Z-SCORE METHOD (threshold={args.zscore_threshold})", args.top_n)
        display_outliers(outliers_percentile, "PERCENTILE METHOD (1%-99%)", args.top_n)
        display_outliers(outliers_modified_zscore, "MODIFIED Z-SCORE METHOD", args.top_n)
        display_outliers(resort_outliers, "RESORT-SPECIFIC OUTLIERS", args.top_n)
        display_outliers(suspicious, "SUSPICIOUS ENTRIES", args.top_n)
        
        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Total records: {len(df)}")
        print(f"IQR outliers: {len(outliers_iqr)} ({len(outliers_iqr)/len(df)*100:.1f}%)")
        print(f"Z-score outliers: {len(outliers_zscore)} ({len(outliers_zscore)/len(df)*100:.1f}%)")
        print(f"Percentile outliers: {len(outliers_percentile)} ({len(outliers_percentile)/len(df)*100:.1f}%)")
        print(f"Modified Z-score outliers: {len(outliers_modified_zscore)} ({len(outliers_modified_zscore)/len(df)*100:.1f}%)")
        print(f"Resort-specific outliers: {len(resort_outliers)} ({len(resort_outliers)/len(df)*100:.1f}%)")
        print(f"Suspicious entries: {len(suspicious)} ({len(suspicious)/len(df)*100:.1f}%)")
        
        # Visualizations
        if not args.quick and (args.show_plots or args.save_plots):
            create_visualizations(df, outliers_iqr, args.save_plots)
        
        # Export outliers
        if args.export_outliers:
            export_outliers(outliers_iqr, 'outliers_iqr.csv')
            export_outliers(outliers_zscore, 'outliers_zscore.csv')
            export_outliers(resort_outliers, 'outliers_resort_specific.csv')
            export_outliers(suspicious, 'outliers_suspicious.csv')
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())