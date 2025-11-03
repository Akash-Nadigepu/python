
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
    
    def generate_summary_excel(self) -> None:
        """Generate summary Excel file with severity counts."""
        print("📊 Generating summary report...")
        
        # Get counts for each team
        dev_counts = self.get_severity_counts(self.dev_team_df)
        sre_counts = self.get_severity_counts(self.sre_team_df)
        db_counts = self.get_severity_counts(self.db_team_df) if self.db_team_df is not None else None
        
        # Get HasExploit counts for SRE team (Critical and High only where HasExploit = Yes/True)
        sre_exploit_counts = self._get_exploit_counts(self.sre_team_df)
        
        # Calculate total counts
        if db_counts:
            total_counts = {
                severity: dev_counts[severity] + sre_counts[severity] + db_counts[severity]
                for severity in ['Total'] + self.SEVERITY_ORDER
            }
        else:
            total_counts = {
                severity: dev_counts[severity] + sre_counts[severity]
                for severity in ['Total'] + self.SEVERITY_ORDER
            }
        
        # Create summary data
        summary_data = {
            'Severity': ['Total', 'Critical', 'High', 'Medium', 'Low', 'None'],
            'Total': [
                total_counts['Total'],
                total_counts['Critical'],
                total_counts['High'],
                total_counts['Medium'],
                total_counts['Low'],
                total_counts['None']
            ],
            'SRE_Team_Label': ['', 'Critical', 'High', 'Medium', 'Low', 'None'],
            'SRE_Team': [
                sre_counts['Total'],
                sre_counts['Critical'],
                sre_counts['High'],
                sre_counts['Medium'],
                sre_counts['Low'],
                sre_counts['None']
            ],
            'HasExploit_True': [
                '',
                sre_exploit_counts.get('Critical', 0),
                sre_exploit_counts.get('High', 0),
                '',
                '',
                ''
            ],
            'Dev_Team_Label': ['', 'Critical', 'High', 'Medium', 'Low', 'None'],
            'Dev_Team': [
                dev_counts['Total'],
                dev_counts['Critical'],
                dev_counts['High'],
                dev_counts['Medium'],
                dev_counts['Low'],
                dev_counts['None']
            ]
        }
        
        # Add DB Team columns if broker portal
        if db_counts:
            summary_data['DB_Team_Label'] = ['', 'Critical', 'High', 'Medium', 'Low', 'None']
            summary_data['DB_Team'] = [
                db_counts['Total'],
                db_counts['Critical'],
                db_counts['High'],
                db_counts['Medium'],
                db_counts['Low'],
                db_counts['None']
            ]
        
        # Create DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        # Generate summary Excel filename
        summary_filename = f'Summary_{self.base_filename}.xlsx'
        
        try:
            with pd.ExcelWriter(summary_filename, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Get workbook to format
                workbook = writer.book
                worksheet = writer.sheets['Summary']
                
                # Set column widths
                worksheet.column_dimensions['A'].width = 12
                worksheet.column_dimensions['B'].width = 12
                worksheet.column_dimensions['C'].width = 15
                worksheet.column_dimensions['D'].width = 12
                worksheet.column_dimensions['E'].width = 18
                worksheet.column_dimensions['F'].width = 15
                worksheet.column_dimensions['G'].width = 12
                
                if db_counts:
                    worksheet.column_dimensions['H'].width = 15
                    worksheet.column_dimensions['I'].width = 12
            
            print(f"✓ Summary: {summary_filename}")
            
        except Exception as e:
            print(f"❌ Error generating summary file: {str(e)}")
            raise
    
    def _get_exploit_counts(self, df: pd.DataFrame) -> dict:
        """Get counts of records where HasExploit = Yes/True for Critical and High severity."""
        if df is None or len(df) == 0:
            return {}
        
        # Check if HasExploit column exists
        if 'HasExploit' not in df.columns:
            return {}
        
        # Filter for HasExploit = Yes or True (case-insensitive)
        exploit_mask = df['HasExploit'].astype(str).str.lower().isin(['yes', 'true'])
        exploit_df = df[exploit_mask]
        
        # Count by severity
        counts = {}
        for severity in ['Critical', 'High']:
            count = len(exploit_df[exploit_df['VendorSeverity'] == severity])
            if count > 0:
                counts[severity] = count
        
        return counts
    
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
