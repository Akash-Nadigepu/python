import sys
import pandas as pd
import os

def main():
    # Verify command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python code.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Check file extension and read appropriately
    try:
        if input_file.lower().endswith(".csv"):
            df = pd.read_csv(input_file)
        elif input_file.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(input_file)
        else:
            print("Error: Unsupported file format. Please use .csv, .xls, or .xlsx")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Clean up column names for uniformity
    df.columns = df.columns.str.strip()

    # Validate required columns
    required_columns = ['AssetName', 'LocationPath', 'VendorSeverity']
    for col in required_columns:
        if col not in df.columns:
            print(f"Error: Required column '{col}' not found in the input file.")
            sys.exit(1)

    # Primary filtering (AssetName)
    bamboo_df = df[df['AssetName'].str.lower() == 'bamboo']
    db_team_df = df[df['AssetName'].str.lower() != 'bamboo']

    # Secondary filtering for Bamboo group (Dev vs SRE)
    dev_df = bamboo_df[bamboo_df['LocationPath'].str.contains('.m2|xml-data', case=False, na=False)]
    sre_df = bamboo_df[~bamboo_df['LocationPath'].str.contains('.m2|xml-data', case=False, na=False)]

    # Severity categories
    severity_levels = ['Critical', 'High', 'Medium', 'Low', 'None']

    # Print severity distribution for each team
    for team_name, team_df in [('Dev Team', dev_df), ('SRE Team', sre_df), ('DB Team', db_team_df)]:
        print(f"\n=== {team_name} ===")
        severity_counts = team_df['VendorSeverity'].value_counts().reindex(severity_levels, fill_value=0)
        print(severity_counts)
        print(f"Total: {len(team_df)}")

    # Save output reports
    dev_file = "Dev_Team_Report.xlsx"
    sre_file = "SRE_Team_Report.xlsx"
    db_file = "DB_Team_Report.xlsx"

    dev_df.to_excel(dev_file, index=False)
    sre_df.to_excel(sre_file, index=False)
    db_team_df.to_excel(db_file, index=False)

    print(f"\nReports generated successfully:\n  - {dev_file}\n  - {sre_file}\n  - {db_file}")

if __name__ == "__main__":
    main()
