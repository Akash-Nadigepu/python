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

def get_severity_series(df, name):
    """
    Calculates severity counts for a DataFrame and ensures all required
    severity levels ('Critical', 'High', 'Medium', 'Low', 'None') are present,
    filling missing ones with 0.
    """
    required_severities = ['Critical', 'High', 'Medium', 'Low', 'None']

    # Standardize severity column: Fill missing/NaT with 'None', clean whitespace
    # Note: We rely on the input having 'Critical', 'High', etc., names.
    counts = df[COL_SEVERITY].astype(str).str.strip().value_counts()
    
    # Reindex to ensure all required severities are present, filling missing with 0,
    # and rename the series for concatenation.
    counts = counts.reindex(required_severities, fill_value=0).rename(name)
    return counts

def print_severity_table(report_df):
    """
    Prints the multi-column severity report in a clean, aligned console table.
    """
    print("=" * 75)
    print(f"| {'SEVERITY':<10} | {'TOTAL':>15} | {'SRE TEAM':>15} | {'DEV TEAM':>15} | {'DB TEAM':>15} |")
    print("=" * 75)

    # Print each severity row
    for severity in report_df.index:
        row = report_df.loc[severity]
        print(
            f"| {severity:<10} | "
            f"{row['Total']:>15,} | "
            f"{row['SRE Team']:>15,} | "
            f"{row['Dev Team']:>15,} | "
            f"{row['DB Team']:>15,} |"
        )

    # Print the final sum row
    total_sum = report_df.sum()
    print("-" * 75)
    print(
        f"| {'GRAND SUM':<10} | "
        f"{total_sum['Total']:>15,} | "
        f"{total_sum['SRE Team']:>15,} | "
        f"{total_sum['Dev Team']:>15,} | "
        f"{total_sum['DB Team']:>15,} |"
    )
    print("=" * 75)


def process_wiz_report(file_path):
    """
    Loads a Wiz report CSV, filters it into three teams (Dev, SRE, DB),
    generates separate Excel files, and prints a multi-column severity summary.
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
    print(f"Successfully loaded {total_records:,} total records.")
    print("-" * 50)


    # 2. Filtering and Segmentation Logic

    # --- LEVEL 1: DB Team vs. Dev/SRE Pool ---
    # DB Team: Asset Name (Y) does NOT contain 'bamboo' (case-insensitive)
    df_db_team = df[~df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()
    
    # Dev/SRE Pool: Asset Name (Y) DOES contain 'bamboo'
    df_dev_sre_pool = df[df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()


    # --- LEVEL 2: Dev Team vs. SRE Team (within the Dev/SRE Pool) ---
    
    # Dev Team: Location Path (Q) contains '.m2' OR 'xml-data' (case-insensitive)
    dev_filter = df_dev_sre_pool[COL_LOCATION].str.contains(r'\.m2|xml-data', case=False, na=False)
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
            print(f"  - {team_name} report saved to '{file_name}' ({len(team_df):,} records)")
        except Exception as e:
            print(f"  - ERROR: Failed to write {team_name} report to {file_name}. Details: {e}")

    print("-" * 50)
    
    
    # 4. Console Reporting (Multi-Column Severity Table)
    
    # Calculate counts for all four groups
    s_total = get_severity_series(df, 'Total')
    s_sre = get_severity_series(df_sre_team, 'SRE Team')
    s_dev = get_severity_series(df_dev_team, 'Dev Team')
    s_db = get_severity_series(df_db_team, 'DB Team')

    # Combine into a single DataFrame
    report_df = pd.concat([s_total, s_sre, s_dev, s_db], axis=1)

    print("Multi-Column Severity Count Report:")
    print_severity_table(report_df)
    
    print("Processing complete.")


if __name__ == "__main__":
    # Check if a file path argument was provided
    if len(sys.argv) != 2:
        print("Usage: python wiz_report_processor.py \"<path_to_wiz_report.csv>\"")
        sys.exit(1)
    
    # Get the file path from the command-line arguments
    input_file_path = sys.argv[1]
    process_wiz_report(input_file_path)
