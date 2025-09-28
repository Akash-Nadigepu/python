import pandas as pd
import os
import re
import sys

# --- Configuration ---
OUTPUT_DIRECTORY = 'Triage_Vulnerability_Reports'

# Confirmed Column Headers (based on I, Q, Y, AT positions)
COLUMN_SEVERITY = 'Severity'
COLUMN_LOCATION_PATH = 'LocationPath'
COLUMN_ASSET_NAME = 'AssetName'
COLUMN_SUBSCRIPTION = 'SubscriptionName'
COLUMNS_TO_USE = [COLUMN_SEVERITY, COLUMN_LOCATION_PATH, COLUMN_ASSET_NAME, COLUMN_SUBSCRIPTION]
# ---------------------

def triage_vulnerabilities(input_path, output_dir):
    """
    Reads the full vulnerability list from the input file path, 
    categorizes it into four types, and generates separate CSV reports 
    with a severity count summary printed to the console.
    """
    print(f"Starting triage for file: {input_path}")
    
    # 1. Read the Data (Using column names and low_memory=False to handle DtypeWarning/size)
    try:
        df = pd.read_csv(
            input_path, 
            usecols=COLUMNS_TO_USE, 
            low_memory=False, 
            encoding='utf-8' 
        )
            
    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{input_path}'. Please check the path and filename.")
        return
    except ValueError as e:
        # This error typically means a column name was misspelled or the header changed.
        print(f"ERROR reading file: One or more required column headers were not found.")
        print(f"Please confirm the file contains: {', '.join(COLUMNS_TO_USE)}")
        print(f"Details: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during file reading: {e}")
        return

    total_rows = len(df)
    print(f"Successfully read {total_rows} total records.")
    
    # --- Data Cleaning and Normalization ---
    df[COLUMN_ASSET_NAME] = df[COLUMN_ASSET_NAME].fillna('').astype(str)
    df[COLUMN_SUBSCRIPTION] = df[COLUMN_SUBSCRIPTION].fillna('').astype(str)
    df[COLUMN_LOCATION_PATH] = df[COLUMN_LOCATION_PATH].fillna('').astype(str)
    # Standardize Severity column
    df[COLUMN_SEVERITY] = df[COLUMN_SEVERITY].fillna('None').astype(str).str.title()
    
    os.makedirs(output_dir, exist_ok=True)

    # --- 2. Define Category Filters (Triage Logic) ---

    # 2A. Primary Split: Database (DB) vs. CI/CD Support (Non-DB)
    is_db_asset = df[COLUMN_ASSET_NAME].str.contains('db|mongo', case=False)
    db_assets = df[is_db_asset].copy()
    cicd_assets = df[~is_db_asset].copy()

    # 1. DB PROD vs. NON-PROD: Prod = 'plat' (Platinum)
    is_prod_sub = db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', case=False)
    db_prod_df = db_assets[is_prod_sub]
    db_non_prod_df = db_assets[~is_prod_sub]

    # 2. CI/CD DEV BUILD vs. DEVOPS TOOLING: Dev Build = '.m2' OR 'xml' in LocationPath
    # These paths indicate application dependencies/config (Dev Team focus)
    dev_build_mask = cicd_assets[COLUMN_LOCATION_PATH].str.contains(r'\.m2|xml', regex=True, case=False)
    cicd_dev_build_df = cicd_assets[dev_build_mask]
    cicd_devops_tooling_df = cicd_assets[~dev_build_mask] # Base OS/Agents (DevOps/SRE Team focus)

    # --- 3. Write to New Files and Generate Report ---

    category_data = {
        'DB_Production_Vulnerabilities': db_prod_df,
        'DB_NonProduction_Vulnerabilities': db_non_prod_df,
        'CI_CD_DevBuild_Vulnerabilities': cicd_dev_build_df,
        'CI_CD_DevOpsTooling_Vulnerabilities': cicd_devops_tooling_df
    }
    
    severity_order = ['Critical', 'High', 'Medium', 'Low', 'None']
    
    print("\n" + "="*50)
    print("      VULNERABILITY TRIAGE AND SEVERITY SUMMARY")
    print("="*50)
    print(f"{'Category':<35} | {'Critical':<10} | {'High':<10} | {'Medium':<10} | {'Low':<10} | {'None':<10} | {'Total':<10}")
    print("-" * 110)

    for category_name, df_slice in category_data.items():
        # Calculate severity counts
        severity_counts = df_slice[COLUMN_SEVERITY].value_counts().reindex(severity_order, fill_value=0)
        
        # Prepare data for printing
        counts = severity_counts.to_dict()
        total_for_category = sum(counts.values())
        
        # Print the severity counts to the console in the required neat format
        print(f"{category_name:<35} | {counts.get('Critical', 0):<10} | {counts.get('High', 0):<10} | {counts.get('Medium', 0):<10} | {counts.get('Low', 0):<10} | {counts.get('None', 0):<10} | {total_for_category:<10}")

        # Write the file (Outputting as CSV)
        output_filename = f"{output_dir}/{category_name}.csv"
        df_slice[COLUMNS_TO_USE].to_csv(output_filename, index=False, encoding='utf-8')
        
    print("-" * 110)
    print("\n✅ Processing complete. All categorized files are saved in the 'Triage_Vulnerability_Reports' directory as CSV.")

# --- Execute the script, reading the argument from the command line ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python <script_name.py> <input_file.csv>")
        print("Example: python triage_script.py wizreport.csv")
        sys.exit(1)
        
    # sys.argv[1] is the first argument after the script name
    input_file_path = sys.argv[1]
    triage_vulnerabilities(input_file_path, OUTPUT_DIRECTORY)
