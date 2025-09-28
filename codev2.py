import pandas as pd
import os
import sys

# --- Configuration ---
# NOTE: We now get the INPUT_FILE path from the command line argument (sys.argv[1])
# Default fallback name (if needed for testing, but should be overridden by argument)
# INPUT_FILE = 'vulnerability_list.csv' 
OUTPUT_DIRECTORY = 'Vulnerability_Reports'

# IMPORTANT: Replace these generic names with the *actual* column headers from your Excel file.
# Based on your previous context:
COLUMN_ASSET_NAME = 'AssetName'       # Column Y, used for DB vs CI/CD split
COLUMN_SUBSCRIPTION = 'SubscriptionName' # Column AT, used for Prod vs Non-Prod split
COLUMN_LOCATION_PATH = 'LocationPath'  # Column Q, used for Dev vs DevOps split
COLUMN_SEVERITY = 'Severity'         # Column I, used for final count report
# ---------------------

def triage_vulnerabilities(input_path, output_dir):
    """
    Reads the full vulnerability list (CSV format assumed), categorizes it into four types, 
    and generates separate Excel reports with a severity count summary.
    """
    print(f"Starting triage for file: {input_path}")
    
    # 1. Read the Data (Updated to read CSV)
    try:
        # Use pd.read_csv for CSV files. Assuming headers are present.
        df = pd.read_csv(input_path)
        
        # Ensure all required columns are present
        required_cols = [COLUMN_ASSET_NAME, COLUMN_SUBSCRIPTION, COLUMN_LOCATION_PATH, COLUMN_SEVERITY]
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            print(f"ERROR: Missing required columns in the CSV file: {missing_cols}")
            return
            
    except FileNotFoundError:
        print(f"ERROR: Input file not found at {input_path}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    total_rows = len(df)
    print(f"Successfully read {total_rows} total records.")
    
    # Data Cleaning and Preparation (as before)
    df[COLUMN_ASSET_NAME] = df[COLUMN_ASSET_NAME].fillna('')
    df[COLUMN_SUBSCRIPTION] = df[COLUMN_SUBSCRIPTION].fillna('')
    df[COLUMN_LOCATION_PATH] = df[COLUMN_LOCATION_PATH].fillna('')

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    # --- 2. Define Category Filters (Boolean Logic) ---

    # 2A. Primary Split: Database (DB) vs. CI/CD Support (Non-DB)
    df['is_db_asset'] = df[COLUMN_ASSET_NAME].str.contains('db|mongo', case=False, na=False)
    db_assets = df[df['is_db_asset']]
    cicd_assets = df[~df['is_db_asset']]

    # --- 2B. Secondary Splits ---

    # 1. DB PROD vs. DB NON-PROD
    # Prod = Platinum ('plat'), Non-Prod = everything else (Gold/Silver)
    db_prod_df = db_assets[db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', case=False, na=False)]
    db_non_prod_df = db_assets[~db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', case=False, na=False)]

    # 2. CI/CD DEV BUILD vs. CI/CD DEVOPS TOOLING
    # Dev Build = LocationPath contains '.m2' or 'xml'
    dev_path_keywords = ['.m2', 'xml'] 
    is_dev_build = cicd_assets[COLUMN_LOCATION_PATH].apply(lambda x: any(keyword in x for keyword in dev_path_keywords))
    
    cicd_dev_build_df = cicd_assets[is_dev_build]
    cicd_devops_tooling_df = cicd_assets[~is_dev_build]

    # --- 3. Write to New Files and Generate Report ---

    category_data = {
        'DB_Production_Vulnerabilities': db_prod_df,
        'DB_NonProduction_Vulnerabilities': db_non_prod_df,
        'CI_CD_DevBuild_Vulnerabilities': cicd_dev_build_df,
        'CI_CD_DevOpsTooling_Vulnerabilities': cicd_devops_tooling_df
    }
    
    full_severity_report = {}

    print("\n--- Generating Categorized Excel Reports ---")
    for category_name, df_slice in category_data.items():
        # Get severity counts for the current category 
        severity_counts = df_slice[COLUMN_SEVERITY].value_counts().reindex(['Critical', 'High', 'Medium', 'Low', 'None'], fill_value=0)
        full_severity_report[category_name] = severity_counts.to_dict()
        
        # Write the Excel file (using 'openpyxl' engine to write to .xlsx)
        output_filename = f"{output_dir}/{category_name}.xlsx"
        df_slice.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"✅ Created file: {output_filename} with {len(df_slice)} rows.")
    
    # --- 4. Print Summary Report ---

    print("\n" + "="*50)
    print("      VULNERABILITY TRIAGE AND SEVERITY SUMMARY")
    print("="*50)
    print(f"Total Records Processed: {total_rows}\n")

    # Format and print the consolidated report
    print(f"{'Category':<35} | {'Critical':<10} | {'High':<10} | {'Medium':<10} | {'Low':<10} | {'None':<10}")
    print("-" * 100)
    
    # Print data row by row, ensuring consistent formatting
    for category, counts in full_severity_report.items():
        total_for_category = sum(counts.values())
        print(f"{category:<35} | {counts.get('Critical', 0):<10} | {counts.get('High', 0):<10} | {counts.get('Medium', 0):<10} | {counts.get('Low', 0):<10} | {counts.get('None', 0):<10} (Total: {total_for_category})")
        
    print("="*50)

# --- Execute the script using command-line arguments ---
if __name__ == "__main__":
    # Check if a filename was provided as an argument
    if len(sys.argv) < 2:
        print("\nERROR: Please provide the input CSV filename as a command-line argument.")
        print("Usage: python vuln_analysis.py <input_filename.csv>")
        sys.exit(1)
        
    # sys.argv[0] is the script name; sys.argv[1] is the first argument (the filename)
    input_filename = sys.argv[1]
    
    # Ensure necessary libraries are installed
    try:
        import pandas as pd
        import openpyxl # Used by pandas to write .xlsx output
    except ImportError:
        print("\nERROR: Required libraries (pandas and openpyxl) are not installed.")
        print("Please run: pip install pandas openpyxl")
        sys.exit(1)

    triage_vulnerabilities(input_filename, OUTPUT_DIRECTORY)
