import pandas as pd
import os
import sys

# --- Configuration (File Names for Output) ---
DEV_TEAM_FILE = "dev_team_report.xlsx"
SRE_TEAM_FILE = "sre_team_report.xlsx"
DATABASE_TEAM_FILE = "database_team_report.xlsx"

def analyze_and_filter_report(input_csv):
    """
    Loads the Wiz report, applies filtering logic to assign teams, 
    generates three separate Excel reports, and prints severity counts.
    """
    if not os.path.exists(input_csv):
        print(f"Error: Input file not found at '{input_csv}'")
        return

    print(f"--- 1. Loading Data from {input_csv} ---")
    
    # Load data
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Clean column names by stripping leading/trailing whitespace
    df.columns = df.columns.str.strip()
    
    # Define the core columns needed (assuming case-sensitivity after stripping)
    ASSET_NAME_COL = 'AssetName'
    LOCATION_PATH_COL = 'LocationPath'
    VENDOR_SEVERITY_COL = 'VendorSeverity'
    
    # Ensure key columns exist before proceeding
    required_cols = [ASSET_NAME_COL, LOCATION_PATH_COL, VENDOR_SEVERITY_COL]
    if not all(col in df.columns for col in required_cols):
        print("Error: Missing one or more required columns ('AssetName', 'LocationPath', 'VendorSeverity'). Please check the CSV header.")
        return

    
    print("--- 2. Applying Filtering Logic and Team Assignment ---")
    
    # --- Step 1: Default Assignment (Database Team) ---
    df['Team'] = 'Database Team'
    
    # --- Step 2: Identify Bamboo Assets (Track for Dev/SRE) ---
    # Case=False for case-insensitive matching in AssetName
    bamboo_assets = df[ASSET_NAME_COL].str.contains('bamboo', case=False, na=False)
    
    # --- Step 3: Second Level Filter (Dev vs SRE) ---
    # Condition for Dev Team: LocationPath contains '.m2' OR 'xml-data'
    # Use str.contains with regex=True for '.m2' to treat '.' literally
    dev_path_condition = (
        df[LOCATION_PATH_COL].astype(str).str.contains(r'\.m2', regex=True, case=False) |
        df[LOCATION_PATH_COL].astype(str).str.contains('xml-data', case=False)
    )
    
    # --- Step 4: Assign Dev Team ---
    # Records must be bamboo_assets AND meet the dev_path_condition
    df.loc[bamboo_assets & dev_path_condition, 'Team'] = 'Dev Team'
    
    # --- Step 5: Assign SRE Team ---
    # Records must be bamboo_assets AND NOT meet the dev_path_condition
    df.loc[bamboo_assets & (~dev_path_condition), 'Team'] = 'SRE Team'
    
    print(f"Total Records Processed: {len(df)}")
    print("Team Distribution:")
    print(df['Team'].value_counts())
    
    
    print("\n--- 3. Generating Excel Reports ---")
    
    # Filter DataFrames for each team
    # Drop the temporary 'Team' column before exporting
    df_dev = df[df['Team'] == 'Dev Team'].drop(columns=['Team'])
    df_sre = df[df['Team'] == 'SRE Team'].drop(columns=['Team'])
    df_database = df[df['Team'] == 'Database Team'].drop(columns=['Team'])

    # Save to Excel files
    df_dev.to_excel(DEV_TEAM_FILE, index=False)
    print(f"Generated {DEV_TEAM_FILE} with {len(df_dev)} records.")
    
    df_sre.to_excel(SRE_TEAM_FILE, index=False)
    print(f"Generated {SRE_TEAM_FILE} with {len(df_sre)} records.")
    
    df_database.to_excel(DATABASE_TEAM_FILE, index=False)
    print(f"Generated {DATABASE_TEAM_FILE} with {len(df_database)} records.")

    
    print("\n--- 4. Severity Count Report (VendorSeverity) ---")
    
    # Calculate counts by VendorSeverity (case-insensitive)
    severity_counts = df[VENDOR_SEVERITY_COL].astype(str).str.lower().value_counts().rename('Count')
    
    # Define the required order and categories
    required_severities = ['critical', 'high', 'medium', 'low', 'none']
    
    # Create a Series with the required index, filling missing values with 0
    severity_report = pd.Series(0, index=required_severities, name='Count').add(severity_counts, fill_value=0).astype(int)
    
    # Print the report
    print("Vulnerability Count by Vendor Severity (All Teams):")
    print("-" * 40)
    for severity, count in severity_report.items():
        # Capitalize for cleaner output
        print(f"{severity.capitalize():<10}: {count:>8}")
        
    print("-" * 40)
    print(f"Total Records: {len(df):>10}")
    print("-" * 40)

if __name__ == '__main__':
    # Check if the input file path was provided as a command-line argument
    if len(sys.argv) < 2:
        print("Error: Please provide the input CSV file path as a command-line argument.")
        print('Example usage: python wiz_report_analyzer.py "wiz report.xlsx - Sheet1.csv"')
        sys.exit(1)
        
    # The input file path is the second argument (index 1)
    input_file_path = sys.argv[1]
    
    # Execute the main function with the provided file path
    analyze_and_filter_report(input_file_path)
