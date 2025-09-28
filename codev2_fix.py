import pandas as pd
import os
import sys
import re

# --- Configuration ---
# Output folder will be dynamically created: Vulnerability_Reports_<Month>
OUTPUT_BASE_DIRECTORY = 'Vulnerability_Reports'

# IMPORTANT: These column names must match the EXACT headers in your CSV.
COLUMN_ASSET_NAME = 'AssetName'       
COLUMN_SUBSCRIPTION = 'SubscriptionName' 
COLUMN_LOCATION_PATH = 'LocationPath'  
COLUMN_SEVERITY = 'Severity'         
# ---------------------

def extract_month_shortcut(filename_or_path):
    """
    Extracts a 3-letter month shortcut (e.g., 'Aug') by looking for known month 
    abbreviations anywhere in the string. This is the most permissive fix for OS masking issues.
    """
    # List of all standard 3-letter month abbreviations
    month_abbreviations = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    
    # New Permissive Regex: Looks for a month abbreviation (case-insensitive)
    # The '([A-Za-z]+)' part captures the full word, and we specifically look for the 
    # 3-letter shortcut in the list of standard abbreviations.
    month_match = re.search(month_abbreviations, filename_or_path, re.IGNORECASE)
    
    if month_match:
        # Returns the found month shortcut in Title Case (e.g., 'Aug')
        return month_match.group(1).title()
    return None

def triage_vulnerabilities(input_path, output_dir_base):
    """
    Reads the full vulnerability list from a CSV file (given by input_path), 
    categorizes it into four types, generates separate Excel reports, 
    and prints a severity count summary.
    """
    # 1. Dynamic Month Extraction and Output Setup
    # Pass the entire input_path to the extractor for the best chance of finding the month
    filename_for_search = os.path.basename(input_path)
    month_shortcut = extract_month_shortcut(filename_for_search)
    
    if month_shortcut:
        output_dir = f"{output_dir_base}_{month_shortcut}"
        print(f"Detected month: {month_shortcut}. Output folder: {output_dir}")
    else:
        output_dir = output_dir_base
        print("Warning: Could not detect month in filename. Using generic output folder.")
        
    print(f"Starting analysis for file: {input_path}")
    
    # 2. Read the Data (pd.read_csv with low_memory=False to suppress DtypeWarning)
    try:
        df = pd.read_csv(input_path, low_memory=False)
        
        required_cols = [COLUMN_ASSET_NAME, COLUMN_SUBSCRIPTION, COLUMN_LOCATION_PATH, COLUMN_SEVERITY]
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            print(f"ERROR: Missing required columns in the CSV file: {missing_cols}")
            return
            
    except FileNotFoundError:
        print(f"ERROR: Input file not found at {input_path}. Please check the path and filename.")
        return

    total_rows = len(df)
    print(f"Successfully read {total_rows} total records.")
    
    # Clean up and normalize key columns
    df[COLUMN_ASSET_NAME] = df[COLUMN_ASSET_NAME].astype(str).str.lower().fillna('')
    df[COLUMN_SUBSCRIPTION] = df[COLUMN_SUBSCRIPTION].astype(str).str.lower().fillna('')
    df[COLUMN_LOCATION_PATH] = df[COLUMN_LOCATION_PATH].astype(str).str.lower().fillna('')
    df[COLUMN_SEVERITY] = df[COLUMN_SEVERITY].astype(str).str.title().fillna('None')


    # Create the output directory 
    os.makedirs(output_dir, exist_ok=True)

    # --- 3. Define Category Filters (Logic remains the same) ---

    df['is_db_asset'] = df[COLUMN_ASSET_NAME].str.contains('db|mongo', na=False)
    db_assets = df[df['is_db_asset']]
    cicd_assets = df[~df['is_db_asset']] 

    db_prod_df = db_assets[db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]
    db_non_prod_df = db_assets[~db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]

    dev_path_keywords = ['.m2', 'xml'] 
    is_dev_build = cicd_assets[COLUMN_LOCATION_PATH].apply(lambda x: any(keyword in x for keyword in dev_path_keywords))
    
    cicd_dev_build_df = cicd_assets[is_dev_build]
    cicd_devops_tooling_df = cicd_assets[~is_dev_build]

    # --- 4. Write to New Files and Generate Report ---

    category_templates = {
        'DB_Production': db_prod_df,
        'DB_NonProduction': db_non_prod_df,
        'CI_CD_DevBuild': cicd_dev_build_df,
        'CI_CD_DevOpsTooling': cicd_devops_tooling_df
    }
    
    full_severity_report = {}

    print("\n--- Generating Categorized Excel Reports ---")
    for category_base_name, df_slice in category_templates.items():
        severity_counts = df_slice[COLUMN_SEVERITY].value_counts().reindex(['Critical', 'High', 'Medium', 'Low', 'None'], fill_value=0)
        full_severity_report[category_base_name] = severity_counts.to_dict()
        
        # New Naming Convention: BaseName_Month.xlsx (e.g., DB_Production_Aug.xlsx)
        month_suffix = f"_{month_shortcut}" if month_shortcut else ""
        output_filename = f"{output_dir}/{category_base_name}{month_suffix}.xlsx"
        
        # Write the Excel file
        df_slice.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Created file: {output_filename} with {len(df_slice)} rows.")
    
    # --- 5. Print Summary Report (remains the same) ---

    print("\n" + "="*50)
    print("      VULNERABILITY SEVERITY SUMMARY")
    print("="*50)
    print(f"Total Records Processed: {total_rows}\n")

    # Format and print the consolidated report
    print(f"{'Category':<35} | {'Critical':<10} | {'High':<10} | {'Medium':<10} | {'Low':<10} | {'None':<10}")
    print("-" * 100)
    
    for category, counts in full_severity_report.items():
        total_for_category = sum(counts.values())
        print(f"{category:<35} | {counts.get('Critical', 0):<10} | {counts.get('High', 0):<10} | {counts.get('Medium', 0):<10} | {counts.get('Low', 0):<10} | {counts.get('None', 0):<10} (Total: {total_for_category})")
        
    print("="*50)


# --- Execution Block: Reads the Argument ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nERROR: Missing input file path.")
        print("Usage: python your_script_name.py <path/to/your/report.csv>")
        sys.exit(1)
        
    input_file_path = sys.argv[1]
    triage_vulnerabilities(input_file_path, OUTPUT_BASE_DIRECTORY)
