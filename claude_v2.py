import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
import warnings

# Suppress openpyxl warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


class WizReportAnalyzer:
    """Analyzes and filters Wiz vulnerability reports by team."""
    
    SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'None']
    
    def __init__(self, input_file: str):
        """Initialize analyzer with input file path."""
        self.input_file = Path(input_file)
        self.df = None
        self.dev_team_df = None
        self.sre_team_df = None
        self.db_team_df = None
        self.month_name = self._extract_month_from_filename()
        
    def load_data(self) -> None:
        """Load CSV file with error handling."""
        try:
            print(f"📂 Loading file: {self.input_file.name}")
            self.df = pd.read_csv(self.input_file)
            print(f"✓ Successfully loaded {len(self.df)} records")
            if self.month_name:
                print(f"✓ Detected month: {self.month_name}\n")
            else:
                print()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Error: File '{self.input_file}' not found")
        except pd.errors.EmptyDataError:
            raise ValueError("❌ Error: The CSV file is empty")
        except Exception as e:
            raise Exception(f"❌ Error reading CSV file: {str(e)}")
    
    def validate_columns(self) -> None:
        """Validate required columns exist."""
        required_columns = ['AssetName', 'LocationPath', 'VendorSeverity']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        
        if missing_columns:
            raise ValueError(f"❌ Error: Missing required columns: {', '.join(missing_columns)}")
    
    def filter_teams(self) -> None:
        """Apply team filtration logic."""
        print("🔍 Applying team filtration logic...")
        
        # Clean data - handle NaN values
        self.df['AssetName'] = self.df['AssetName'].fillna('')
        self.df['LocationPath'] = self.df['LocationPath'].fillna('')
        self.df['VendorSeverity'] = self.df['VendorSeverity'].fillna('None')
        
        # Normalize severity values
        self.df['VendorSeverity'] = self.df['VendorSeverity'].replace({
            'none': 'None',
            'info': 'None',
            'Info': 'None'
        })
        
        # First level filtration: Check if AssetName contains "bamboo" (case-insensitive)
        bamboo_mask = self.df['AssetName'].str.lower().str.contains('bamboo', na=False, regex=False)
        
        # Second level filtration for bamboo assets: Check LocationPath
        dev_mask = bamboo_mask & (
            self.df['LocationPath'].str.contains('.m2', na=False, regex=False) |
            self.df['LocationPath'].str.contains('xml-data', na=False, regex=False)
        )
        
        sre_mask = bamboo_mask & ~dev_mask
        
        # DB Team: exclude bamboo AND exclude tableau assets (case-insensitive)
        tableau_mask = self.df['AssetName'].str.lower().str.contains('tableau', na=False, regex=False)
        db_mask = ~bamboo_mask & ~tableau_mask
        
        # Debug: Print tableau asset count
        tableau_count = tableau_mask.sum()
        if tableau_count > 0:
            print(f"ℹ️  Excluded {tableau_count} Tableau assets from DB Team")
        
        # Split dataframes
        self.dev_team_df = self.df[dev_mask].copy()
        self.sre_team_df = self.df[sre_mask].copy()
        self.db_team_df = self.df[db_mask].copy()
        
        print(f"✓ Dev Team: {len(self.dev_team_df)} records")
        print(f"✓ SRE Team: {len(self.sre_team_df)} records")
        print(f"✓ DB Team: {len(self.db_team_df)} records\n")
    
    def get_severity_counts(self, df: pd.DataFrame) -> Dict[str, int]:
        """Get counts for each severity level."""
        severity_counts = df['VendorSeverity'].value_counts().to_dict()
        
        # Ensure all severity levels are present
        counts = {severity: severity_counts.get(severity, 0) for severity in self.SEVERITY_ORDER}
        counts['Total'] = len(df)
        
        return counts
    
    def generate_excel_reports(self) -> None:
        """Generate separate Excel files for each team."""
        print("📊 Generating Excel reports...")
        
        # Determine month suffix
        month_suffix = f"_{self.month_name}" if self.month_name else ""
        
        reports = [
            (f'Dev_Team{month_suffix}.xlsx', self.dev_team_df, 'Dev Team'),
            (f'SRE_Team{month_suffix}.xlsx', self.sre_team_df, 'SRE Team'),
            (f'DB_Team{month_suffix}.xlsx', self.db_team_df, 'DB Team')
        ]
        
        for filename, df, team_name in reports:
            try:
                output_path = Path(filename)
                df.to_excel(output_path, index=False, engine='openpyxl')
                print(f"✓ {team_name}: {filename} ({len(df)} records)")
            except Exception as e:
                print(f"❌ Error generating {filename}: {str(e)}")
                raise
        
        print()
    
    def print_summary_table(self) -> None:
        """Print professional multi-column summary table."""
        # Get counts for each team
        dev_counts = self.get_severity_counts(self.dev_team_df)
        sre_counts = self.get_severity_counts(self.sre_team_df)
        db_counts = self.get_severity_counts(self.db_team_df)
        
        # Calculate total counts
        total_counts = {
            severity: dev_counts[severity] + sre_counts[severity] + db_counts[severity]
            for severity in ['Total'] + self.SEVERITY_ORDER
        }
        
        # Print header
        print("=" * 95)
        print("VULNERABILITY SUMMARY BY TEAM AND SEVERITY".center(95))
        print("=" * 95)
        
        # Column headers
        print(f"{'Severity':<12} │ {'Total':>10} │ {'SRE Team':>10} │ {'Dev Team':>10} │ {'DB Team':>10}")
        print("─" * 95)
        
        # Print Total row first
        print(f"{'TOTAL':<12} │ {total_counts['Total']:>10,} │ {sre_counts['Total']:>10,} │ "
              f"{dev_counts['Total']:>10,} │ {db_counts['Total']:>10,}")
        print("─" * 95)
        
        # Print severity rows
        for severity in self.SEVERITY_ORDER:
            emoji = self._get_severity_emoji(severity)
            print(f"{emoji} {severity:<9} │ {total_counts[severity]:>10,} │ {sre_counts[severity]:>10,} │ "
                  f"{dev_counts[severity]:>10,} │ {db_counts[severity]:>10,}")
        
        print("=" * 95)
        
        # Print percentage breakdown
        if total_counts['Total'] > 0:
            print("\nSeverity Distribution (%):")
            critical_pct = (total_counts['Critical'] / total_counts['Total']) * 100
            high_pct = (total_counts['High'] / total_counts['Total']) * 100
            medium_pct = (total_counts['Medium'] / total_counts['Total']) * 100
            low_pct = (total_counts['Low'] / total_counts['Total']) * 100
            none_pct = (total_counts['None'] / total_counts['Total']) * 100
            
            print(f"  Critical: {critical_pct:>6.2f}% │ High: {high_pct:>6.2f}% │ "
                  f"Medium: {medium_pct:>6.2f}% │ Low: {low_pct:>6.2f}% │ None: {none_pct:>6.2f}%")
            print()
    
    @staticmethod
    def _get_severity_emoji(severity: str) -> str:
        """Get emoji for severity level."""
        emoji_map = {
            'Critical': '🔴',
            'High': '🟠',
            'Medium': '🟡',
            'Low': '🟢',
            'None': '⚪'
        }
        return emoji_map.get(severity, '⚫')
    
    def _extract_month_from_filename(self) -> str:
        """Extract month name from filename (e.g., 'Oct', 'Aug', 'Sep')."""
        import re
        
        # Exact 3-letter month abbreviations (case-insensitive)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Get the full filename including path
        filename = str(self.input_file)
        
        # Search for month pattern anywhere in the filename (case-insensitive)
        for month in months:
            # Use case-insensitive search
            pattern = re.compile(month, re.IGNORECASE)
            if pattern.search(filename):
                return month
        
        return None
    
    def run(self) -> None:
        """Execute the complete analysis workflow."""
        try:
            self.load_data()
            self.validate_columns()
            self.filter_teams()
            self.generate_excel_reports()
            self.print_summary_table()
            print("✅ Analysis completed successfully!\n")
            
        except Exception as e:
            print(f"\n{str(e)}\n")
            sys.exit(1)


def main():
    """Main entry point."""
    print("\n" + "=" * 95)
    print("WIZ VULNERABILITY REPORT ANALYZER".center(95))
    print("=" * 95 + "\n")
    
    # Check command-line arguments
    if len(sys.argv) != 2:
        print("❌ Usage: python code.py <input_csv_file>")
        print("Example: python code.py wiz_report.csv\n")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Check if file exists
    if not Path(input_file).exists():
        print(f"❌ Error: File '{input_file}' does not exist\n")
        sys.exit(1)
    
    # Run analyzer
    analyzer = WizReportAnalyzer(input_file)
    analyzer.run()


if __name__ == "__main__":
    main()
