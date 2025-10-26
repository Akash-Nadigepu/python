import sys
import pandas as pd
from tabulate import tabulate

def main():
    try:
        # Validate command-line argument
        if len(sys.argv) < 2:
            print("❌ Error: Please provide the input CSV file.\nUsage: python code.py 'wiz_report.csv'")
            sys.exit(1)

        file_path = sys.argv[1]

        # Read CSV file
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            sys.exit(1)

        # Check required columns
        required_cols = ["AssetName", "Location path", "VendorSeverity"]
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ Error: Missing required column '{col}' in input file.")
                sys.exit(1)

        # Normalize column names
        df.columns = df.columns.str.strip()

        # --- Filter DB Team ---
        db_team = df[~df["AssetName"].str.contains("bamboo", case=False, na=False)]

        # --- Filter bamboo assets ---
        bamboo_df = df[df["AssetName"].str.contains("bamboo", case=False, na=False)]

        # --- Split between Dev and SRE ---
        dev_team = bamboo_df[bamboo_df["Location path"].str.contains(r"\.m2|xml-data", case=False, na=False)]
        sre_team = bamboo_df[~bamboo_df["Location path"].str.contains(r"\.m2|xml-data", case=False, na=False)]

        # --- Function to get severity counts ---
        def severity_counts(sub_df):
            counts = sub_df["VendorSeverity"].str.lower().value_counts()
            return {
                "Critical": counts.get("critical", 0),
                "High": counts.get("high", 0),
                "Medium": counts.get("medium", 0),
                "Low": counts.get("low", 0),
                "None": counts.get("none", 0),
            }

        # --- Compute stats ---
        teams = {"SRE Team": sre_team, "Dev Team": dev_team, "DB Team": db_team}
        table_data = []

        for team_name, team_df in teams.items():
            counts = severity_counts(team_df)
            total = sum(counts.values())
            table_data.append([
                team_name,
                counts["Critical"],
                counts["High"],
                counts["Medium"],
                counts["Low"],
                counts["None"],
                total
            ])

        # --- Save Excel files ---
        dev_team.to_excel("Dev_Team.xlsx", index=False)
        sre_team.to_excel("SRE_Team.xlsx", index=False)
        db_team.to_excel("DB_Team.xlsx", index=False)

        # --- Print professional summary ---
        headers = ["Team", "Critical", "High", "Medium", "Low", "None", "Total"]
        print("\n📊  WIZ REPORT SUMMARY\n")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", numalign="right"))
        print("\n✅ Files generated: Dev_Team.xlsx, SRE_Team.xlsx, DB_Team.xlsx")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
