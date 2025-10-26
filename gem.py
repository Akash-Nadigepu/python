
import sys
import os
import argparse
import pandas as pd

# ---- Helpers ----
def exit_err(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def find_column(df, possible_names, fallback_index=None):
    """
    Try to find a column in df among possible_names (case-insensitive).
    If not found and fallback_index provided, return df.columns[fallback_index] if index in range.
    Returns the actual column name or None.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    for n in possible_names:
        if n and n.lower() in cols_lower:
            return cols_lower[n.lower()]
    if fallback_index is not None:
        if 0 <= fallback_index < len(df.columns):
            return df.columns[fallback_index]
    return None

def normalize_severity(val):
    """Map various vendor severity representations to one of:
       'Critical', 'High', 'Medium', 'Low', 'None'
    """
    if pd.isna(val):
        return "None"
    s = str(val).strip()
    if s == "":
        return "None"
    l = s.lower()
    if "critical" in l:
        return "Critical"
    if "high" in l:
        return "High"
    if "medium" in l:
        return "Medium"
    if "low" in l:
        return "Low"
    if l in ("none", "na", "n/a"):
        return "None"
    # If unknown, return original label capitalized (but it won't be shown in final 5-row table)
    return s.title()

def count_severities(series, categories_order):
    """Given a series of severities (already normalized), return counts in the given order as dict."""
    vc = series.value_counts(dropna=False)
    return {cat: int(vc.get(cat, 0)) for cat in categories_order}

def print_minimal_table(counts_dict, order):
    """
    counts_dict: dict of column_name -> {severity: count, ...}
    order: list of severities in the exact order to print
    """
    # compute column widths
    col_names = list(counts_dict.keys())
    # header widths
    col_widths = {}
    # severity label width
    label_w = max(len(s) for s in order)
    col_widths['Severity'] = label_w
    for col in col_names:
        max_val_len = max(len(str(counts_dict[col].get(s, 0))) for s in order)
        col_widths[col] = max(len(col), max_val_len)

    # build header
    header = f"{'Severity'.ljust(col_widths['Severity'])}  "
    header += "  ".join(col.ljust(col_widths[col]) for col in col_names)
    sep = "-" * len(header)
    print(header)
    print(sep)
    for sev in order:
        row = sev.ljust(col_widths['Severity']) + "  "
        row += "  ".join(str(counts_dict[col].get(sev, 0)).rjust(col_widths[col]) for col in col_names)
        print(row)

# ---- Main processing ----
def main():
    parser = argparse.ArgumentParser(description="Segment Wiz report into DB/Dev/SRE teams and print severity summary.")
    parser.add_argument("input_path", help="Input CSV or XLSX file path (e.g. wiz_report.csv or wiz_report.xlsx)")
    args = parser.parse_args()

    infile = args.input_path
    if not os.path.isfile(infile):
        exit_err(f"Input file not found: {infile}")

    # read file (CSV or Excel)
    try:
        if infile.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(infile, dtype=str)  # read as strings to avoid type surprises
        else:
            df = pd.read_csv(infile, dtype=str)
    except FileNotFoundError:
        exit_err(f"File not found: {infile}")
    except Exception as e:
        exit_err(f"Failed to read input file '{infile}': {e}")

    if df.shape[0] == 0:
        exit_err("Input file contains no rows.")

    # Attempt to find required columns:
    # The user specified columns by letters: Y (AssetName) -> index 24 (0-based)
    # Q (LocationPath) -> index 16
    # J (VendorSeverity) -> index 9
    # Also accept common header names if available.
    asset_col = find_column(df, ["AssetName", "assetname", "asset name"], fallback_index=24)
    loc_col   = find_column(df, ["LocationPath", "Location Path", "locationpath", "location path"], fallback_index=16)
    sev_col   = find_column(df, ["VendorSeverity", "Vendor Severity", "vendorseverity", "vendor severity"], fallback_index=9)

    missing = []
    if asset_col is None:
        missing.append("AssetName (column Y / index 24)")
    if loc_col is None:
        missing.append("LocationPath (column Q / index 16)")
    if sev_col is None:
        missing.append("VendorSeverity (column J / index 9)")
    if missing:
        exit_err("Missing required columns: " + ", ".join(missing))

    # Work on a copy
    df_work = df.copy()

    # Fill NaN with empty strings for string checks
    df_work[asset_col] = df_work[asset_col].fillna("").astype(str)
    df_work[loc_col]   = df_work[loc_col].fillna("").astype(str)
    df_work[sev_col]   = df_work[sev_col].fillna("")

    # Segmentation:
    # DB Team: AssetName does NOT contain 'bamboo' (case-insensitive)
    # Dev/SRE pool: AssetName contains 'bamboo'
    # From pool:
    #   Dev Team: LocationPath contains '.m2' OR 'xml-data'
    #   SRE Team: remaining assets in pool
    asset_lower = df_work[asset_col].str.lower()
    loc_lower   = df_work[loc_col].str.lower()

    is_bamboo = asset_lower.str.contains("bamboo", na=False)
    in_db_team = ~is_bamboo
    pool = df_work[is_bamboo]

    # define dev criteria
    dev_mask = loc_lower.str.contains(".m2", na=False) | loc_lower.str.contains("xml-data", na=False)
    # but dev_mask applied only for pool (bamboo)
    dev_mask_pool = is_bamboo & dev_mask
    sre_mask_pool = is_bamboo & ~dev_mask

    df_db  = df_work[in_db_team].copy()
    df_dev = df_work[dev_mask_pool].copy()
    df_sre = df_work[sre_mask_pool].copy()

    # Normalize severity field for counting
    df_work["___severity_norm__"] = df_work[sev_col].apply(normalize_severity)
    df_db["___severity_norm__"]   = df_db[sev_col].apply(normalize_severity)
    df_dev["___severity_norm__"]  = df_dev[sev_col].apply(normalize_severity)
    df_sre["___severity_norm__"]  = df_sre[sev_col].apply(normalize_severity)

    # Save Excel outputs
    out_db = "db_team.xlsx"
    out_dev = "dev_team.xlsx"
    out_sre = "sre_team.xlsx"
    try:
        # drop the helper col before saving original columns (but keep it if you want)
        save_db = df_db.drop(columns=["__severity_norm__"], errors="ignore")
        save_dev = df_dev.drop(columns=["__severity_norm__"], errors="ignore")
        save_sre = df_sre.drop(columns=["__severity_norm__"], errors="ignore")

        save_db.to_excel(out_db, index=False)
        save_dev.to_excel(out_dev, index=False)
        save_sre.to_excel(out_sre, index=False)
    except Exception as e:
        exit_err(f"Failed to write Excel output files: {e}")

    # Build summary counts
    categories = ["Critical", "High", "Medium", "Low", "None"]

    counts_total = count_severities(df_work["___severity_norm__"], categories)
    counts_sre   = count_severities(df_sre["___severity_norm__"], categories)
    counts_dev   = count_severities(df_dev["___severity_norm__"], categories)
    counts_db    = count_severities(df_db["___severity_norm__"], categories)

    counts = {
        "Total": counts_total,
        "SRE Team": counts_sre,
        "Dev Team": counts_dev,
        "DB Team": counts_db
    }

    # Print minimal, aligned table
    print("\nSeverity summary (very accurate counts for the five required categories):\n")
    print_minimal_table(counts, categories)

    # Final summary lines
    print("\nSaved Excel files:")
    print(f" - {out_db}  ({len(df_db)} rows)")
    print(f" - {out_dev}  ({len(df_dev)} rows)")
    print(f" - {out_sre}  ({len(df_sre)} rows)")

if __name__ == "__main__":
    main()
