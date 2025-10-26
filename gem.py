import sys
import pandas as pd
from tabulate import tabulate
import os

def main():
    if len(sys.argv) != 2:
        print("Usage: python wiz_segment.py <wiz_report.csv>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    try:
        # auto-detect CSV or Excel
        df = pd.read_csv(input_file) if input_file.endswith('.csv') else pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    required_cols = ['AssetName', 'LocationPath', 'VendorSeverity']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}' in input file.")
            sys.exit(1)

    # Normalize
    df['AssetName'] = df['AssetName'].astype(str).str.lower()
    df['LocationPath'] = df['LocationPath'].astype(str).str.lower()
    df['VendorSeverity'] = df['VendorSeverity'].astype(str).str.title()

    # Segmentation logic
    dev_team = df[(df['AssetName'].str.contains('bamboo')) &
                  (df['LocationPath'].str.contains('.m2') | df['LocationPath'].str.contains('xml-data'))]

    sre_team = df[(df['AssetName'].str.contains('bamboo')) &
                  ~(df['LocationPath'].str.contains('.m2') | df['LocationPath'].str.contains('xml-data'))]

    db_team = df[~df['AssetName'].str.contains('bamboo')]

    # Save to Excel
    try:
        dev_team.to_excel('Dev_Team_Report.xlsx', index=False)
        sre_team.to_excel('SRE_Team_Report.xlsx', index=False)
        db_team.to_excel('DB_Team_Report.xlsx', index=False)
    except Exception as e:
        print(f"Error writing Excel reports: {e}")
        sys.exit(1)

    # Severity levels
    severities = ['Critical', 'High', 'Medium', 'Low', 'None']
    table_data = []

    for sev in severities:
        sre_count = (sre_team['VendorSeverity'] == sev).sum()
        dev_count = (dev_team['VendorSeverity'] == sev).sum()
        db_count = (db_team['VendorSeverity'] == sev).sum()
        total = sre_count + dev_count + db_count
        table_data.append([sev, sre_count, dev_count, db_count, total])

    # Add grand total row
    total_sre = sre_team.shape[0]
    total_dev = dev_team.shape[0]
    total_db = db_team.shape[0]
    grand_total = total_sre + total_dev + total_db
    table_data.append(['Total', total_sre, total_dev, total_db, grand_total])

    # Print professional formatted summary
    print("\nWIZ SEGMENTATION SUMMARY\n")
    print(tabulate(
        table_data,
        headers=["Severity", "SRE Team", "Dev Team", "DB Team", "Total"],
        tablefmt="grid",
        numalign="right",
        stralign="center"
    ))

    print("\nExcel Reports Generated:")
    print(" - Dev_Team_Report.xlsx")
    print(" - SRE_Team_Report.xlsx")
    print(" - DB_Team_Report.xlsx")

if __name__ == "__main__":
    main()

