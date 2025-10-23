import sys
import pandas as pd

# --- Validate argument ---
if len(sys.argv) < 2:
    print("Usage: python code.py <inputfile.csv or .xlsx>")
    sys.exit(1)

input_file = sys.argv[1]

# --- Read input ---
if input_file.endswith(".xlsx"):
    df = pd.read_excel(input_file)
else:
    df = pd.read_csv(input_file)

# Normalize column names (strip spaces)
df.columns = df.columns.str.strip()

# --- Extract columns ---
asset_col = 'Y AssestName'
path_col = 'Q Location path'
severity_col = 'J VendorSeverity'

# --- Split into groups ---
bamboo_df = df[df[asset_col].str.contains("bamboo", case=False, na=False)]
non_bamboo_df = df[~df[asset_col].str.contains("bamboo", case=False, na=False)]

# --- Dev Team ---
dev_df = bamboo_df[bamboo_df[path_col].str.contains(r'\.m2|xml-data', case=False, na=False)]

# --- SRE Team ---
sre_df = bamboo_df[~bamboo_df[path_col].str.contains(r'\.m2|xml-data', case=False, na=False)]

# --- DevOps Team (Database bucket) ---
devops_df = non_bamboo_df.copy()

# --- Save to Excel ---
dev_df.to_excel("dev_team.xlsx", index=False)
sre_df.to_excel("sre_team.xlsx", index=False)
devops_df.to_excel("devops_team.xlsx", index=False)

# --- Print severity summary ---
def print_summary(name, data):
    print(f"\n{name} Team Summary:")
    counts = data[severity_col].value_counts(dropna=False)
    for sev in ["Critical", "High", "Medium", "Low", "None"]:
        print(f"{sev}: {counts.get(sev, 0)}")
    print(f"Total: {len(data)}")

print_summary("Dev", dev_df)
print_summary("SRE", sre_df)
print_summary("DevOps", devops_df)
