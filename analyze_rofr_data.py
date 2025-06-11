#!/usr/bin/env python3
"""
ROFR Data Analysis Tool

This script provides analysis and visualization of ROFR (Right of First Refusal) data
scraped from DisBoards DVC threads.
"""

import os
import sys
import csv
import argparse
import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dateutil.parser import parse


class ROFRAnalyzer:
    """Analyzer for ROFR data"""
    
    def __init__(self, data_file: str):
        """
        Initialize the analyzer.
        
        Args:
            data_file: Path to the CSV file with ROFR data
        """
        if not os.path.exists(data_file):
            print(f"Error: File {data_file} not found")
            sys.exit(1)
            
        self.data_file = data_file
        self.df = self._load_data()
        
    def _load_data(self) -> pd.DataFrame:
        """
        Load ROFR data from CSV file.
        
        Returns:
            DataFrame with the ROFR data
        """
        df = pd.read_csv(self.data_file)
        
        # Convert formatted dates to datetime
        for date_col in ['sent_date', 'result_date']:
            if date_col in df.columns:
                # Handle dates in YYYY-MM-DD format
                df[date_col] = pd.to_datetime(df[date_col], format='%Y-%m-%d', errors='coerce')
        
        # Convert numeric columns
        for num_col in ['price_per_point', 'total_cost', 'points']:
            if num_col in df.columns:
                df[num_col] = pd.to_numeric(df[num_col], errors='coerce')
        
        # Add year and quarter columns
        if 'sent_date' in df.columns:
            df['year'] = df['sent_date'].apply(
                lambda x: x.year if pd.notna(x) else None
            )
            df['quarter'] = df['sent_date'].apply(
                lambda x: f"Q{(x.month-1)//3+1}-{x.year}" if pd.notna(x) else None
            )
        
        # Clean resort codes
        if 'resort' in df.columns:
            df['resort'] = df['resort'].str.strip()
            
        # Add ROFR decision time
        if 'sent_date' in df.columns and 'result_date' in df.columns:
            df['decision_days'] = df.apply(
                lambda row: (row['result_date'] - row['sent_date']).days 
                if pd.notna(row['sent_date']) and pd.notna(row['result_date']) 
                else None, 
                axis=1
            )
        
        return df
    
    def _parse_date(self, date_str: str) -> datetime.datetime:
        """
        Parse date strings in various formats.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed datetime object
        """
        if not date_str or pd.isna(date_str):
            return None
            
        try:
            # Handle MM/YY format
            if len(date_str) <= 5 and '/' in date_str:
                month, year = date_str.split('/')
                # Assume 20xx for years
                full_year = int(f"20{year}")
                return datetime.datetime(full_year, int(month), 1)
            else:
                # Try standard parsing
                return parse(date_str, fuzzy=True)
        except Exception:
            print(f"Warning: Could not parse date '{date_str}'")
            return None
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the ROFR data.
        
        Returns:
            Dictionary with basic stats
        """
        stats = {}
        
        # Total entries
        stats['total_entries'] = len(self.df)
        
        # Results breakdown
        if 'result' in self.df.columns:
            result_counts = self.df['result'].value_counts().to_dict()
            stats['results'] = result_counts
            
            # Calculate ROFR rates
            if 'passed' in result_counts and 'taken' in result_counts:
                total_decided = result_counts.get('passed', 0) + result_counts.get('taken', 0)
                if total_decided > 0:
                    stats['rofr_rate'] = result_counts.get('taken', 0) / total_decided * 100
        
        # Resort breakdown
        if 'resort' in self.df.columns:
            stats['resorts'] = self.df['resort'].value_counts().to_dict()
        
        # Price statistics
        if 'price_per_point' in self.df.columns:
            stats['price_per_point'] = {
                'mean': self.df['price_per_point'].mean(),
                'median': self.df['price_per_point'].median(),
                'min': self.df['price_per_point'].min(),
                'max': self.df['price_per_point'].max()
            }
        
        # Points statistics
        if 'points' in self.df.columns:
            stats['points'] = {
                'mean': self.df['points'].mean(),
                'median': self.df['points'].median(),
                'min': self.df['points'].min(),
                'max': self.df['points'].max()
            }
            
        # Decision time statistics
        if 'decision_days' in self.df.columns:
            decision_days = self.df['decision_days'].dropna()
            if len(decision_days) > 0:
                stats['decision_days'] = {
                    'mean': decision_days.mean(),
                    'median': decision_days.median(),
                    'min': decision_days.min(),
                    'max': decision_days.max()
                }
        
        return stats
    
    def plot_price_trends(self, output_file: Optional[str] = None) -> None:
        """
        Plot price trends over time.
        
        Args:
            output_file: Path to save the plot (optional)
        """
        if 'resort' not in self.df.columns or 'price_per_point' not in self.df.columns:
            print("Error: Missing required columns for price trend analysis")
            return
            
        # Filter to top 10 most common resorts
        top_resorts = self.df['resort'].value_counts().nlargest(10).index.tolist()
        df_top = self.df[self.df['resort'].isin(top_resorts)]
        
        # Group by quarter and resort to get average prices
        if 'quarter' in self.df.columns:
            plt.figure(figsize=(12, 8))
            
            # Plot price trends by quarter for each resort
            for resort in top_resorts:
                resort_data = df_top[df_top['resort'] == resort]
                if len(resort_data) < 3:  # Skip resorts with very few data points
                    continue
                    
                quarterly_avg = resort_data.groupby('quarter')['price_per_point'].mean()
                plt.plot(quarterly_avg.index, quarterly_avg.values, marker='o', label=resort)
            
            plt.title('Average Price per Point by Quarter')
            plt.xlabel('Quarter')
            plt.ylabel('Price per Point ($)')
            plt.xticks(rotation=45)
            plt.legend(title='Resort')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            if output_file:
                plt.savefig(output_file)
            else:
                plt.show()
    
    def plot_rofr_rates(self, output_file: Optional[str] = None) -> None:
        """
        Plot ROFR rates by resort.
        
        Args:
            output_file: Path to save the plot (optional)
        """
        if 'resort' not in self.df.columns or 'result' not in self.df.columns:
            print("Error: Missing required columns for ROFR rate analysis")
            return
            
        # Filter out pending entries
        df_decided = self.df[self.df['result'].isin(['passed', 'taken'])]
        
        # Calculate ROFR rates by resort
        rofr_rates = []
        for resort in df_decided['resort'].unique():
            resort_data = df_decided[df_decided['resort'] == resort]
            if len(resort_data) < 5:  # Skip resorts with very few data points
                continue
                
            taken_count = len(resort_data[resort_data['result'] == 'taken'])
            total_count = len(resort_data)
            rofr_rate = taken_count / total_count * 100
            rofr_rates.append((resort, rofr_rate, total_count))
        
        # Sort by ROFR rate
        rofr_rates.sort(key=lambda x: x[1], reverse=True)
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        resorts = [r[0] for r in rofr_rates]
        rates = [r[1] for r in rofr_rates]
        counts = [r[2] for r in rofr_rates]
        
        # Create bar chart with counts as colors
        bars = plt.bar(resorts, rates, alpha=0.7)
        
        # Adjust colors based on sample size
        min_count = min(counts)
        max_count = max(counts)
        for i, (bar, count) in enumerate(zip(bars, counts)):
            # Normalize the count to determine the color intensity
            intensity = 0.3 + 0.7 * (count - min_count) / (max_count - min_count) if max_count > min_count else 0.7
            bar.set_color(plt.cm.Blues(intensity))
            
            # Add the count on top of each bar
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'n={count}', ha='center', va='bottom', fontsize=8)
        
        plt.title('ROFR Rates by Resort')
        plt.xlabel('Resort')
        plt.ylabel('ROFR Rate (%)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
    
    def plot_price_distribution(self, output_file: Optional[str] = None) -> None:
        """
        Plot price distribution by resort.
        
        Args:
            output_file: Path to save the plot (optional)
        """
        if 'resort' not in self.df.columns or 'price_per_point' not in self.df.columns:
            print("Error: Missing required columns for price distribution analysis")
            return
            
        # Filter to top 10 most common resorts
        top_resorts = self.df['resort'].value_counts().nlargest(10).index.tolist()
        df_top = self.df[self.df['resort'].isin(top_resorts)]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Box plot of prices by resort
        sns.boxplot(x='resort', y='price_per_point', data=df_top)
        
        # Add swarm plot on top for individual data points
        sns.swarmplot(x='resort', y='price_per_point', data=df_top, 
                     size=4, color='.3', alpha=0.6)
        
        plt.title('Price per Point Distribution by Resort')
        plt.xlabel('Resort')
        plt.ylabel('Price per Point ($)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
    
    def analyze_resort(self, resort_code: str) -> None:
        """
        Analyze data for a specific resort.
        
        Args:
            resort_code: Resort code to analyze
        """
        # Filter data for the specified resort
        resort_df = self.df[self.df['resort'] == resort_code]
        
        if len(resort_df) == 0:
            print(f"No data found for resort {resort_code}")
            return
            
        print(f"\n=== Analysis for {resort_code} ===")
        print(f"Total entries: {len(resort_df)}")
        
        # Results breakdown
        if 'result' in resort_df.columns:
            result_counts = resort_df['result'].value_counts()
            print("\nResults breakdown:")
            for result, count in result_counts.items():
                print(f"  {result}: {count}")
            
            # Calculate ROFR rate
            decided = result_counts.get('passed', 0) + result_counts.get('taken', 0)
            if decided > 0:
                rofr_rate = result_counts.get('taken', 0) / decided * 100
                print(f"\nROFR rate: {rofr_rate:.2f}%")
        
        # Price statistics
        if 'price_per_point' in resort_df.columns:
            price_stats = resort_df['price_per_point'].describe()
            print("\nPrice per point statistics:")
            print(f"  Mean: ${price_stats['mean']:.2f}")
            print(f"  Median: ${price_stats['50%']:.2f}")
            print(f"  Min: ${price_stats['min']:.2f}")
            print(f"  Max: ${price_stats['max']:.2f}")
            
            # Compare passed vs. taken prices
            if 'result' in resort_df.columns:
                passed_df = resort_df[resort_df['result'] == 'passed']
                taken_df = resort_df[resort_df['result'] == 'taken']
                
                if len(passed_df) > 0 and len(taken_df) > 0:
                    passed_avg = passed_df['price_per_point'].mean()
                    taken_avg = taken_df['price_per_point'].mean()
                    print(f"\nAverage price for passed contracts: ${passed_avg:.2f}")
                    print(f"Average price for taken contracts: ${taken_avg:.2f}")
                    print(f"Difference: ${passed_avg - taken_avg:.2f}")
        
        # Points statistics
        if 'points' in resort_df.columns:
            points_stats = resort_df['points'].describe()
            print("\nPoints statistics:")
            print(f"  Mean: {points_stats['mean']:.1f}")
            print(f"  Median: {points_stats['50%']:.1f}")
            print(f"  Min: {points_stats['min']:.1f}")
            print(f"  Max: {points_stats['max']:.1f}")
        
        # Decision time statistics
        if 'decision_days' in resort_df.columns:
            decision_days = resort_df['decision_days'].dropna()
            if len(decision_days) > 0:
                decision_stats = decision_days.describe()
                print("\nDecision time statistics (days):")
                print(f"  Mean: {decision_stats['mean']:.1f}")
                print(f"  Median: {decision_stats['50%']:.1f}")
                print(f"  Min: {decision_stats['min']:.1f}")
                print(f"  Max: {decision_stats['max']:.1f}")
    
    def run_analysis(self, output_dir: Optional[str] = None) -> None:
        """
        Run comprehensive analysis and generate reports.
        
        Args:
            output_dir: Directory to save output files (optional)
        """
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Print basic statistics
        stats = self.get_basic_stats()
        print("\n=== ROFR Data Analysis ===")
        print(f"Total entries: {stats['total_entries']}")
        
        if 'results' in stats:
            print("\nResults breakdown:")
            for result, count in stats['results'].items():
                print(f"  {result}: {count}")
            
            if 'rofr_rate' in stats:
                print(f"\nOverall ROFR rate: {stats['rofr_rate']:.2f}%")
        
        if 'resorts' in stats:
            print("\nTop 10 resorts by number of entries:")
            for resort, count in sorted(stats['resorts'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {resort}: {count}")
        
        if 'price_per_point' in stats:
            print("\nPrice per point statistics:")
            for stat, value in stats['price_per_point'].items():
                print(f"  {stat}: ${value:.2f}")
        
        if 'decision_days' in stats:
            print("\nDecision time statistics (days):")
            for stat, value in stats['decision_days'].items():
                print(f"  {stat}: {value:.1f}")
        
        # Generate plots
        if output_dir:
            self.plot_price_trends(os.path.join(output_dir, 'price_trends.png'))
            self.plot_rofr_rates(os.path.join(output_dir, 'rofr_rates.png'))
            self.plot_price_distribution(os.path.join(output_dir, 'price_distribution.png'))
        else:
            print("\nGenerating plots...")
            self.plot_price_trends()
            self.plot_rofr_rates()
            self.plot_price_distribution()
        
        # Analyze top 5 resorts
        if 'resorts' in stats:
            top_resorts = sorted(stats['resorts'].items(), key=lambda x: x[1], reverse=True)[:5]
            for resort, _ in top_resorts:
                self.analyze_resort(resort)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Analyze ROFR data from DisBoards')
    parser.add_argument('data_file', type=str, help='CSV file with ROFR data')
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                      help='Directory to save output files')
    parser.add_argument('--resort', '-r', type=str, default=None,
                      help='Analyze specific resort')
    
    args = parser.parse_args()
    
    analyzer = ROFRAnalyzer(args.data_file)
    
    if args.resort:
        analyzer.analyze_resort(args.resort)
    else:
        analyzer.run_analysis(args.output_dir)


if __name__ == "__main__":
    main()