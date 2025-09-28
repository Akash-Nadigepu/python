import pandas as pd
import os
import sys

# --- Configuration ---
# INPUT_FILE is now expected as the first command-line argument (sys.argv[1])
# We only define the output directory and the column names (which should be static headers)

OUTPUT_DIRECTORY = 'Vulnerability_Reports'

# IMPORTANT: These column names must match the EXACT headers in CSV.
COLUMN_ASSET_NAME = 'AssetName'       
COLUMN_SUBSCRIPTION = 'SubscriptionName' 
COLUMN_LOCATION_PATH = 'LocationPath'  
COLUMN_SEVERITY = 'Severity'         
# ---------------------

def triage_vulnerabilities(input_path, output_dir):
    """
    Reads the full vulnerability list from a CSV file (given by input_path), 
    categorizes it into four types, generates separate Excel reports, 
    and prints a severity count summary.
    """
    print(f"Starting analysis for file: {input_path}")
    
    # 1. Read the Data (FIXED: pd.read_csv with low_memory=False to suppress DtypeWarning)
    try:
        # Use pd.read_csv for CSV files. low_memory=False ensures correct reading of large files.
        df = pd.read_csv(input_path, low_memory=False)
        
        # Ensure all required columns are present in the DataFrame
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


    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # --- 2. Define Category Filters (Boolean Logic) ---

    # 2A. Primary Split: Database (DB) vs. CI/CD Support (Non-DB)
    df['is_db_asset'] = df[COLUMN_ASSET_NAME].str.contains('db|mongo', na=False)
    
    db_assets = df[df['is_db_asset']]
    cicd_assets = df[~df['is_db_asset']] 

    # 2B. Secondary Splits

    # 1. DB PROD vs. DB NON-PROD (Based on SubscriptionName 'plat' for Platinum)
    db_prod_df = db_assets[db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]
    db_non_prod_df = db_assets[~db_assets[COLUMN_SUBSCRIPTION].str.contains('plat', na=False)]

    # 2. CI/CD DEV BUILD vs. CI/CD DEVOPS TOOLING
    # Dev Build = LocationPath contains '.m2' (Maven) or 'xml' (config)
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
        # Get severity counts for the current category before writing the file
        severity_counts = df_slice[COLUMN_SEVERITY].value_counts().reindex(['Critical', 'High', 'Medium', 'Low', 'None'], fill_value=0)
        full_severity_report[category_name] = severity_counts.to_dict()
        
        # Write the Excel file
        output_filename = f"{output_dir}/{category_name}.xlsx"
        df_slice.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Created file: {output_filename} with {len(df_slice)} rows.")
    
    # --- 4. Print Summary Report ---

    print("\n" + "="*50)
    print("      VULNERABILITY SEVERITY SUMMARY")
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


# --- Execution Block: Reads the Argument ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nERROR: Missing input file path.")
        print("Usage: python your_script_name.py <path/to/your/report.csv>")
        sys.exit(1)
        
    # sys.argv[1] is the first argument passed after the script name
    input_file_path = sys.argv[1]
    triage_vulnerabilities(input_file_path, OUTPUT_DIRECTORY)
