import pandas as pd
import sys
import os

# --- Constants for assumed column names ---
COL_SEVERITY = 'Vendor Severity' # Column J
COL_LOCATION = 'Location Path'   # Column Q
COL_ASSET_NAME = 'Asset Name'     # Column Y

def get_severity_series(df, name):
    """
    Calculates severity counts for a DataFrame, explicitly handles missing values
    as 'None', and ensures all required severity levels are present.
    """
    required_severities = ['Critical', 'High', 'Medium', 'Low', 'None']
    
    # 1. Handle missing/NaN values by filling them with the string 'None'
    # 2. Convert to string and clean whitespace
    severity_data = df[COL_SEVERITY].fillna('None').astype(str).str.strip()

    # 3. Calculate counts
    counts = severity_data.value_counts()
    
    # 4. Filter for only the required severities (in case other non-standard severities exist)
    counts = counts.filter(items=required_severities)

    # 5. Reindex to ensure all 5 required severities are present, fill missing with 0
    counts = counts.reindex(required_severities, fill_value=0).rename(name)
    return counts

def print_severity_table(report_df):
    """
    Prints the multi-column severity report in a clean, minimal, aligned console table.
    """
    # Define widths for consistent, minimal alignment
    W_SEV = 10
    W_COL = 15
    W_TOTAL = W_SEV + (W_COL * 4) + 6 # Total width of the table including separators

    # Separator line
    separator = "-" * W_TOTAL

    print(separator)
    # Header Row
    print(
        f"| {'SEVERITY':<{W_SEV}} "
        f"| {'TOTAL':>{W_COL}} "
        f"| {'SRE TEAM':>{W_COL}} "
        f"| {'DEV TEAM':>{W_COL}} "
        f"| {'DB TEAM':>{W_COL}} |"
    )
    print(separator)

    # Data Rows
    for severity in report_df.index:
        row = report_df.loc[severity]
        # Use comma separator for thousands (e.g., 10,000)
        print(
            f"| {severity:<{W_SEV}} "
            f"| {row['Total']:>{W_COL},} "
            f"| {row['SRE Team']:>{W_COL},} "
            f"| {row['Dev Team']:>{W_COL},} "
            f"| {row['DB Team']:>{W_COL},} |"
        )

    # Footer Row (GRAND SUM)
    total_sum = report_df.sum()
    print(separator)
    print(
        f"| {'TOTAL':<{W_SEV}} "
        f"| {total_sum['Total']:>{W_COL},} "
        f"| {total_sum['SRE Team']:>{W_COL},} "
        f"| {total_sum['Dev Team']:>{W_COL},} "
        f"| {total_sum['DB Team']:>{W_COL},} |"
    )
    print(separator)


def process_wiz_report(file_path):
    """
    Loads a Wiz report CSV, filters it into three teams (Dev, SRE, DB),
    generates separate Excel files, and prints a multi-column severity summary.
    """
    print(f"--- Starting Report Processing for: {file_path} ---")

    # 1. Load Data and Initial Error Handling
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"\nERROR: Input file not found at path: {file_path}")
        return
    except Exception as e:
        print(f"\nERROR: Failed to read CSV file. Check if it is a valid CSV format.")
        print(f"Details: {e}")
        return

    required_cols = [COL_SEVERITY, COL_LOCATION, COL_ASSET_NAME]
    if not all(col in df.columns for col in required_cols):
        print(f"\nERROR: The CSV file is missing one or more required columns.")
        print(f"Expected columns: {required_cols}")
        return

    total_records = len(df)
    print(f"Successfully loaded {total_records:,} total records.")
    print("-" * 50)


    # 2. Filtering and Segmentation Logic

    # DB Team: Asset Name (Y) does NOT contain 'bamboo'
    df_db_team = df[~df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()
    
    # Dev/SRE Pool: Asset Name (Y) DOES contain 'bamboo'
    df_dev_sre_pool = df[df[COL_ASSET_NAME].str.contains('bamboo', case=False, na=False)].copy()


    # Dev Team: Location Path (Q) contains '.m2' OR 'xml-data'
    # Using raw string (r'') for proper regex and escaping the dot in '.m2'
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

    print("Multi-Column Severity Count Report (Minimal Design):")
    print_severity_table(report_df)
    
    print("Processing complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python wiz_report_processor.py \"<path_to_wiz_report.csv>\"")
        sys.exit(1)
    
    input_file_path = sys.argv[1]
    process_wiz_report(input_file_path)
