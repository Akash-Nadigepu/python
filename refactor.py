import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import warnings
from datetime import datetime, timedelta

# Suppress openpyxl warnings

warnings.filterwarnings(‘ignore’, category=UserWarning, module=‘openpyxl’)

class PortalConfig:
“”“Configuration for different portals.”””

```
BROKER = {
    'name': 'Broker',
    'teams': ['Dev', 'SRE', 'DB'],
    'filtration_type': 'asset_based'
}

SHOPPER = {
    'name': 'Shopper',
    'teams': ['Dev', 'SRE'],
    'filtration_type': 'location_based'
}

EMPLOYER = {
    'name': 'Employer',
    'teams': ['Dev', 'SRE'],
    'filtration_type': 'location_based'
}

# Dev team location path keywords
DEV_KEYWORDS = ['.m2', 'npm', 'node', 'xml', 'jar', 'root']

# Broker-specific Dev keywords (more restrictive)
BROKER_DEV_KEYWORDS = ['.m2', 'xml-data']
```

class WizReportAnalyzer:
“”“Analyzes and filters Wiz vulnerability reports by portal and team.”””

```
SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'None']

def __init__(self, input_file: str):
    """Initialize analyzer with input file path."""
    self.input_file = Path(input_file)
    self.base_filename = self.input_file.stem
    self.df: Optional[pd.DataFrame] = None
    self.portal_config: Optional[Dict] = None
    self.portal_name: Optional[str] = None
    self.teams_data: Dict[str, pd.DataFrame] = {}

def load_data(self) -> None:
    """Load CSV file with error handling."""
    try:
        print(f"\n📥 Loading file: {self.input_file.name}")
        self.df = pd.read_csv(self.input_file)
        print(f"✓ Successfully loaded {len(self.df):,} records\n")
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

def add_age_column(self) -> None:
    """Calculate and add Age_Days column to the DataFrame."""
    print("📅 Calculating vulnerability age...")
    
    current_date = pd.Timestamp.now()
    
    def calculate_age(row):
        """Calculate age in days for a single vulnerability."""
        # Parse FirstDetected date
        first_detected = pd.to_datetime(row['FirstDetected'], errors='coerce', utc=True)
        
        if pd.isna(first_detected):
            return None
        
        # Remove timezone info to avoid comparison issues
        first_detected = first_detected.tz_localize(None) if first_detected.tzinfo else first_detected
        
        # Determine end date
        if row.get('FindingStatus') == 'Resolved' and pd.notna(row.get('ResolvedAt')):
            # For resolved items, use ResolvedAt date
            end_date = pd.to_datetime(row['ResolvedAt'], errors='coerce', utc=True)
            if pd.isna(end_date):
                end_date = current_date
            else:
                # Remove timezone info
                end_date = end_date.tz_localize(None) if end_date.tzinfo else end_date
        else:
            # For open/in-progress items, use current date
            end_date = current_date
        
        # Calculate age in days
        age_days = (end_date - first_detected).days
        
        # Prevent negative ages (data quality issue)
        return max(0, age_days)
    
    # Apply age calculation to all rows
    self.df['Age'] = self.df.apply(calculate_age, axis=1)
    
    # Count how many have valid ages
    valid_ages = self.df['Age'].notna().sum()
    print(f"✓ Age calculated for {valid_ages:,} records")
    
    if valid_ages < len(self.df):
        missing_ages = len(self.df) - valid_ages
        print(f"⚠️  {missing_ages} records missing FirstDetected date (Age set to None)")
    
    print()

def select_portal(self) -> None:
    """Interactive portal selection."""
    print("=" * 60)
    print("WIZ REPORT ANALYZER".center(60))
    print("=" * 60)
    print("\nSelect Portal:")
    print("  1. Broker")
    print("  2. Shopper")
    print("  3. Employer")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == '1':
                self.portal_config = PortalConfig.BROKER
                self.portal_name = 'Broker'
                break
            elif choice == '2':
                self.portal_config = PortalConfig.SHOPPER
                self.portal_name = 'Shopper'
                break
            elif choice == '3':
                self.portal_config = PortalConfig.EMPLOYER
                self.portal_name = 'Employer'
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n✓✓ Selected portal: {self.portal_name}\n")

def filter_teams(self) -> None:
    """Apply portal-specific team filtration logic."""
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
    
    if self.portal_config['filtration_type'] == 'asset_based':
        self._filter_broker_teams()
    else:
        self._filter_location_based_teams()
    
    # Display counts
    for team_name, df in self.teams_data.items():
        print(f"✓ {team_name} Team: {len(df):,} records")
    print()

def _filter_broker_teams(self) -> None:
    """Broker-specific filtration: Asset-based + Location-based."""
    # Bamboo assets
    bamboo_mask = self.df['AssetName'].str.lower().str.contains('bamboo', na=False, regex=False)
    
    # Dev: Bamboo assets with specific location paths
    dev_location_mask = pd.Series([False] * len(self.df))
    for keyword in PortalConfig.BROKER_DEV_KEYWORDS:
        dev_location_mask |= self.df['LocationPath'].str.contains(keyword, na=False, regex=False, case=False)
    
    dev_mask = bamboo_mask & dev_location_mask
    
    # SRE: Bamboo assets without dev location paths
    sre_mask = bamboo_mask & ~dev_location_mask
    
    # DB: Non-bamboo, non-tableau assets
    tableau_mask = self.df['AssetName'].str.lower().str.contains('tableau', na=False, regex=False)
    db_mask = ~bamboo_mask & ~tableau_mask
    
    self.teams_data['Dev'] = self.df[dev_mask].copy()
    self.teams_data['SRE'] = self.df[sre_mask].copy()
    self.teams_data['DB'] = self.df[db_mask].copy()

def _filter_location_based_teams(self) -> None:
    """Shopper/Employer filtration: Location-based only."""
    # Dev: Location path contains any dev keywords
    dev_mask = pd.Series([False] * len(self.df))
    for keyword in PortalConfig.DEV_KEYWORDS:
        dev_mask |= self.df['LocationPath'].str.contains(keyword, na=False, regex=False, case=False)
    
    # SRE: Everything else
    sre_mask = ~dev_mask
    
    self.teams_data['Dev'] = self.df[dev_mask].copy()
    self.teams_data['SRE'] = self.df[sre_mask].copy()

def get_severity_counts(self, df: pd.DataFrame) -> Dict[str, int]:
    """Get counts for each severity level."""
    severity_counts = df['VendorSeverity'].value_counts().to_dict()
    
    # Ensure all severity levels are present
    counts = {severity: severity_counts.get(severity, 0) for severity in self.SEVERITY_ORDER}
    counts['Total'] = len(df)
    
    return counts

def get_hasexploit_counts(self, df: pd.DataFrame) -> Tuple[int, int]:
    """Get HasExploit counts for Critical and High severities from HasExploit column."""
    if 'HasExploit' not in df.columns:
        return 0, 0
    
    # Filter where HasExploit = Yes/True
    exploit_mask = df['HasExploit'].astype(str).str.lower().str.strip().isin(['yes', 'true'])
    exploit_df = df[exploit_mask]
    
    critical_count = len(exploit_df[exploit_df['VendorSeverity'] == 'Critical'])
    high_count = len(exploit_df[exploit_df['VendorSeverity'] == 'High'])
    
    return critical_count, high_count

def generate_team_excels(self) -> None:
    """Generate separate Excel files for each team."""
    print("📊 Generating team Excel reports...")
    
    for team_name, df in self.teams_data.items():
        try:
            filename = f"{team_name}_{self.base_filename}.xlsx"
            output_path = Path(filename)
            df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"  ✓ {team_name} Team: {filename} ({len(df):,} records)")
        except Exception as e:
            print(f"  ❌ Error generating {filename}: {str(e)}")
    
    print()

def _build_summary_row(self, team_name: str, severity_counts: Dict[str, int],
                      critical_exploit: int = 0, high_exploit: int = 0) -> List:
    """Build a summary row for a team.
    
    Args:
        team_name: Name of the team
        severity_counts: Dictionary with severity counts
        critical_exploit: Count of critical exploits (default 0)
        high_exploit: Count of high exploits (default 0)
    
    Returns:
        List representing a row in the summary Excel
    """
    return [
        severity_counts['Total'],
        '',  # Empty column
        '',  # Empty column
        severity_counts['Critical'],
        critical_exploit if severity_counts['Critical'] else '',
        '',  # Empty column
        severity_counts['High'],
        high_exploit if severity_counts['High'] else '',
        '',  # Empty column
        severity_counts['Medium'],
        '',  # Empty column
        severity_counts['Low']
    ]

def generate_summary_excel(self) -> None:
    """Generate summary Excel with exact layout from requirements."""
    print("📊 Generating summary Excel report...")
    
    try:
        filename = f"Summary_{self.base_filename}.xlsx"
        
        # Get severity counts for each team
        team_counts = {}
        for team_name, df in self.teams_data.items():
            team_counts[team_name] = self.get_severity_counts(df)
        
        # Get HasExploit counts for SRE team
        sre_critical_exploit, sre_high_exploit = self.get_hasexploit_counts(self.teams_data['SRE'])
        
        # Calculate total counts
        total_counts = {severity: 0 for severity in ['Total'] + self.SEVERITY_ORDER}
        for team_name in self.teams_data.keys():
            for severity in ['Total'] + self.SEVERITY_ORDER:
                total_counts[severity] += team_counts[team_name][severity]
        
        # Build summary data with exact layout
        summary_data = []
        
        if 'DB' in self.teams_data:
            # Broker portal layout (3 teams) - Start with severity rows directly
            # Add severity rows
            for severity in self.SEVERITY_ORDER:
                row = [
                    severity,
                    total_counts[severity],
                    '',
                    severity,
                    team_counts['SRE'][severity],
                    sre_critical_exploit if severity == 'Critical' else (sre_high_exploit if severity == 'High' else ''),
                    '',
                    severity,
                    team_counts['Dev'][severity],
                    '',
                    severity,
                    team_counts['DB'][severity]
                ]
                summary_data.append(row)
        else:
            # Shopper/Employer portal layout (2 teams) - Start with severity rows directly
            # Add severity rows
            for severity in self.SEVERITY_ORDER:
                row = [
                    severity,
                    total_counts[severity],
                    '',
                    severity,
                    team_counts['SRE'][severity],
                    sre_critical_exploit if severity == 'Critical' else (sre_high_exploit if severity == 'High' else ''),
                    '',
                    severity,
                    team_counts['Dev'][severity]
                ]
                summary_data.append(row)
        
        # Create DataFrame and save
        df_summary = pd.DataFrame(summary_data)
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_summary.to_excel(writer, index=False, header=False, sheet_name='Summary')
        
        print(f"  ✓ Summary: {filename}")
        print()
    except Exception as e:
        print(f"  ❌ Error generating summary Excel: {str(e)}")
        raise

def print_completion_summary(self) -> None:
    """Print completion summary to console."""
    print("=" * 60)
    print("ANALYSIS COMPLETED SUCCESSFULLY".center(60))
    print("=" * 60)
    print(f"\n📍 Portal: {self.portal_name}")
    print(f"📄 Input File: {self.input_file.name}")
    print(f"📊 Total Records: {len(self.df):,}")
    print(f"📅 Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📁 Generated Files:")
    for team_name in self.teams_data.keys():
        print(f"   ✓ {team_name}_{self.base_filename}.xlsx")
    print(f"   ✓ Summary_{self.base_filename}.xlsx")
    print(f"\n✅ All files generated successfully!\n")

def run(self) -> None:
    """Execute the complete analysis workflow."""
    try:
        self.select_portal()
        self.load_data()
        self.validate_columns()
        self.add_age_column()
        self.filter_teams()
        self.generate_team_excels()
        self.generate_summary_excel()
        self.print_completion_summary()
    except Exception as e:
        print(f"\n{str(e)}\n")
        sys.exit(1)
```

def main():
“”“Main entry point.”””
# Check command-line arguments
if len(sys.argv) != 2:
print(”\n” + “=” * 60)
print(“WIZ VULNERABILITY REPORT ANALYZER”.center(60))
print(”=” * 60)
print(”\n❌ Usage: python code.py <input_csv_file>”)
print(“Example: python code.py wiz_report.csv\n”)
sys.exit(1)

```
input_file = sys.argv[1]

# Check if file exists
if not Path(input_file).exists():
    print(f"\n❌ Error: File '{input_file}' does not exist\n")
    sys.exit(1)

# Run analyzer
analyzer = WizReportAnalyzer(input_file)
analyzer.run()
```

if **name** == “**main**”:
main()
