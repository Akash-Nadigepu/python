import pandas as pd
import os
import sys
import re

# --- Configuration ---
OUTPUT_BASE_DIRECTORY = 'Vulnerability_Reports'

# IMPORTANT: These column names must match the EXACT headers in your CSV.
COLUMN_ASSET_NAME = 'AssetName'       
COLUMN_SUBSCRIPTION = 'SubscriptionName' 
COLUMN_LOCATION_PATH = 'LocationPath'  
COLUMN_SEVERITY = 'Severity'         
# ---------------------

def extract_metadata(filename_or_path):
    """
    Extracts month shortcut (e.g., 'Aug') and the full date-time string 
    (e.g., '2025_09_24T05_22_34Z') from the input filename.
    """
    metadata = {'month_shortcut': None, 'datetime_suffix': ''}
    
    # 1. Extract Month Shortcut (e.g., Aug)
    month_abbreviations = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    month_match = re.search(month_abbreviations, filename_or_path, re.IGNORECASE)
    if month_match:
        metadata['month_shortcut'] = month_match.group(1).title()
    
    # 2. Extract Date-Time Suffix (e.g., 2025_09_24T05_22_34Z)
    # This targets the YYYY_MM_DDT... pattern typical of machine-generated reports
    datetime_match = re.search(r'(\d{4}_\d{2}_\d{2}T\d{2}_\d{2}_\d{2}Z)', filename_or_path)
    if datetime_match:
        metadata['datetime_suffix'] = datetime_match.group(1).replace('T', '_').replace('Z', '')
        
    return metadata

def triage_vulnerabilities(input_path, output_dir_base):
    """
    Reads the full vulnerability list from a CSV file (given by input_path), 
    categorizes it into four types based on the new logic, and generates 
    separate Excel reports with high-traceability naming.
    """
    # 1. Dynamic Metadata Extraction and Output Setup
    filename = os.path.basename(input_path)
    metadata = extract_metadata(filename)
    month_shortcut = metadata['month_shortcut']
    datetime_suffix = metadata['datetime_suffix']

    # Construct the base output directory name (e.g., Triage_Vulnerability_Reports_Aug)
    month_suffix_dir = f"_{month_shortcut}" if month_shortcut else ""
    output_dir = f"{output_dir_base}{month_suffix_dir}"

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
    
    # Clean up and normalize key columns (all to lowercase for reliable matching)
    df[COLUMN_ASSET_NAME] = df[COLUMN_ASSET_NAME].astype(str).str.lower().fillna('')
    df[COLUMN_SUBSCRIPTION] = df[COLUMN_SUBSCRIPTION].astype(str).str.lower().fillna('')
    df[COLUMN_LOCATION_PATH] = df[COLUMN_LOCATION_PATH].astype(str).str.lower().fillna('')
    df[COLUMN_SEVERITY] = df[COLUMN_SEVERITY].astype(str).str.title().fillna('None')


    # Create the output directory 
    os.makedirs(output_dir, exist_ok=True)

    # --- 3. Define Category Filters (NEW LOGIC) ---

    # 3A. Primary Split: CI/CD (bamboo/tableau) vs. DB (everything else)
    
    # Logic: CI/CD Assets are only those containing 'bamboo' OR 'tableau'
    df['is_cicd_asset'] = df[COLUMN_ASSET_NAME].str.contains('bamboo|tableau', na=False)
    
    cicd_assets = df[df['is_cicd_asset']]
    db_assets = df[~df['is_cicd_asset']] # All other assets are DB assets

    # 3B. Secondary Splits

    # 1. DB PROD vs. DB NON-PROD (Based on SubscriptionName 'plat' for Platinum)
    db_prod_df = db_assets[db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]
    db_non_prod_df = db_assets[~db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]

    # 2. CI/CD DEV BUILD vs. CI/CD DEVOPS TOOLING
    # DEV BUILD: LocationPath contains '.m2' (Maven) or 'xml' (config) -> Development Team
    dev_path_keywords = ['.m2', 'xml', 'cargo.lock'] 
    
    is_dev_build = cicd_assets[COLUMN_LOCATION_PATH].apply(lambda x: any(keyword in x for keyword in dev_path_keywords))
    
    cicd_dev_build_df = cicd_assets[is_dev_build]
    cicd_devops_tooling_df = cicd_assets[~is_dev_build] # Everything else in CI/CD is DevOps/SRE tooling

    # --- 4. Write to New Files and Generate Report ---

    category_templates = {
        'DB_Production_Assets': db_prod_df,
        'DB_NonProduction_Assets': db_non_prod_df,
        'DEV_Application_Dependencies': cicd_dev_build_df,
        'DEVOPS_Platform_Tooling': cicd_devops_tooling_df
    }
    
    # Construct the file suffix: _Aug_2025_09_24_05_22_34.xlsx
    file_trace_suffix = f"_{month_shortcut}_{datetime_suffix}" if month_shortcut else f"_{datetime_suffix}"

    full_severity_report = {}

    print("\n--- Generating Categorized Excel Reports ---")
    for category_base_name, df_slice in category_templates.items():
        # Get severity counts 
        severity_counts = df_slice[COLUMN_SEVERITY].value_counts().reindex(['Critical', 'High', 'Medium', 'Low', 'None'], fill_value=0)
        full_severity_report[category_base_name] = severity_counts.to_dict()
        
        # Final output filename with full traceability suffix
        output_filename = f"{output_dir}/{category_base_name}{file_trace_suffix}.xlsx"
        
        # Write the Excel file
        df_slice.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Created file: {output_filename} with {len(df_slice)} rows.")
    
    # --- 5. Print Summary Report (remains the same) ---

    print("\n" + "="*50)
    print("      VULNERABILITY TRIAGE AND SEVERITY SUMMARY")
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
