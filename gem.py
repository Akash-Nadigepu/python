import pandas as pd
import sys
import os

# --- Constants for assumed column names ---
# NOTE: The script assumes your CSV file has the following headers
# based on the column letters provided (J, Q, Y). Adjust these
# if your actual header names are different.
COL_SEVERITY = 'Vendor Severity' # Column J
COL_LOCATION = 'Location Path'   # Column Q
COL_ASSET_NAME = 'Asset Name'     # Column Y

def process_wiz_report(file_path):
    """
    Loads a Wiz report CSV, filters it into three teams (Dev, SRE, DB),
    generates separate Excel files, and prints a severity summary.
    """
    print(f"--- Starting Report Processing for: {file_path} ---")

    # 1. Load Data and Initial Error Handling
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"\nERROR: Input file not found at path: {file_path}")
        return
    except Exception as e:
        print(f"\nERROR: Failed to read CSV file. Check if it is a valid CSV format.")
        print(f"Details: {e}")
        return

    # Check for mandatory columns
    required_cols = [COL_SEVERITY, COL_LOCATION, COL_ASSET_NAME]
    if not all(col in df.columns for col in required_cols):
        print(f"\nERROR: The CSV file is missing one or more required columns.")
        print(f"Expected columns (based on assumed headers): {required_cols}")
        print(f"Available columns: {list(df.columns)}")
        return

    total_records = len(df)
    print(f"Successfully loaded {total_records} total records.")
    print("-" * 50)


    # 2. Filtering and Segmentation Logic

    # --- LEVEL 1: DB Team vs. Dev/SRE Pool ---
    # DB Team: Asset Name (Y) does NOT contain 'bamboo' (case-insensitive)
    df_db_team = df[~df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()
    
    # Dev/SRE Pool: Asset Name (Y) DOES contain 'bamboo'
    df_dev_sre_pool = df[df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()


    # --- LEVEL 2: Dev Team vs. SRE Team (within the Dev/SRE Pool) ---
    
    # Dev Team: Location Path (Q) contains '.m2' OR 'xml-data' (case-insensitive)
    dev_filter = df_dev_sre_pool[COL_LOCATION].str.contains('.m2|xml-data', case=False, na=False)
    df_dev_team = df_dev_sre_pool[dev_filter].copy()

    # SRE Team: The remainder of the Dev/SRE Pool
    df_sre_team = df_dev_sre_pool[~dev_filter].copy()
    
    
    # 3. Output Generation (Excel Files)
    
    output_files = {
        'DB Team': ('db_team.xlsx', df_db_team),
        'Dev Team': ('dev_team.xlsx', df_dev_team),
        'SRE Team': ('sre_team.xlsx', df_sre_team)
    }

    print("Generating Excel output files...")
    for team_name, (file_name, team_df) in output_files.items():
        try:
            team_df.to_excel(file_name, index=False)
            print(f"  - {team_name} report saved to '{file_name}' ({len(team_df)} records)")
        except Exception as e:
            print(f"  - ERROR: Failed to write {team_name} report to {file_name}. Details: {e}")

    print("-" * 50)
    
    
    # 4. Console Reporting (Severity Count)

    print("Severity Count Report (from original dataset):")
    
    # Standardize severity names and fill missing with 'None'
    severity_map = {
        'Critical': 'Critical',
        'High': 'High',
        'Medium': 'Medium',
        'Low': 'Low',
        # Handles cases where 'None' might be represented differently or is blank
        'N/A': 'None',
        'Informational': 'None' 
    }
    
    # Apply standardization and count
    severity_counts = df[COL_SEVERITY].astype(str).str.strip().replace(severity_map, regex=True).value_counts()
    
    # Ensure all required severity levels are present, even if count is 0
    required_severities = ['Critical', 'High', 'Medium', 'Low', 'None']
    
    # Prepare final display dictionary
    final_counts = {}
    for severity in required_severities:
        final_counts[severity] = severity_counts.get(severity, 0)

    # Sum up totals and print
    total_count_sum = sum(final_counts.values())

    # Print results
    print(f"| {'Severity':<10} | {'Count':>8} |")
    print(f"| {'-'*10} | {'-'*8} |")
    for severity, count in final_counts.items():
        print(f"| {severity:<10} | {count:>8,} |")
    
    print(f"| {'='*10} | {'='*8} |")
    print(f"| {'TOTAL':<10} | {total_count_sum:>8,} |")
    print("-" * 50)
    print("Processing complete.")


if __name__ == "__main__":
    # Check if a file path argument was provided
    if len(sys.argv) != 2:
        print("Usage: python wiz_report_processor.py \"<path_to_wiz_report.csv>\"")
        sys.exit(1)
    
    # Get the file path from the command-line arguments
    input_file_path = sys.argv[1]
    process_wiz_report(input_file_path)
