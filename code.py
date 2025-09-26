import pandas as pd
import os
import re
import sys

# --- Configuration: Adjust these variables for your environment ---
# Directory where the categorized Excel files will be saved.
OUTPUT_DIRECTORY = 'Categorized_Vulnerabilities_Simplified'

# Column header for asset names. This must be exact.
ASSET_NAME_COLUMN = 'AssetName'
# -----------------------------------------------------------------

# --- Pattern Matching Logic ---
# This function categorizes each asset name into a simplified group.
# The order of the `if/elif` statements is important for correct matching.
def get_asset_category(asset_name):
    """Categorizes an asset name into a simplified, action-oriented group."""
    if not isinstance(asset_name, str):
        return "00_UNCATEGORIZED_ASSETS"

    name = asset_name.upper()

    # Priority 1: Production Databases
    if 'PROD' in name and any(db in name for db in ['MDB', 'COMDB', 'QUOTEDB']):
        return "10_Production_Databases"
    
    # Priority 2: UAT, SIT, and Dev Environments
    if any(env in name for env in ['UAT', 'SIT', 'DEV']):
        return "30_UAT_SIT_DEV_Environments"

    # Priority 3: Specific Applications & Tools
    if name.startswith("BROKER_PORTAL_"):
        return "20_BrokerPortal_Application_Servers"
    if 'BAMBOO' in name or 'TAOKEN-SERVICE' in name or 'TABLEAU' in name:
        return "40_CI_CD_And_Support_Tools"
    if 'MADE' in name or 'SALES-HIVE-MONGO' in name:
        return "50_MADE_Application_Databases"

    # Default category for anything that doesn't match a specific pattern
    return "00_UNCATEGORIZED_ASSETS"

def sanitize_filename(filename):
    """
    Cleans a string to be a safe filename by removing invalid characters.
    """
    # Replace invalid characters with an underscore
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Trim leading/trailing whitespace
    safe_name = safe_name.strip()
    return safe_name

def process_vulnerability_report(input_file, asset_column, output_dir):
    """
    Reads a large CSV report, applies pattern matching to categorize rows,
    and saves each category to a separate Excel file.
    """
    print(f"Starting to process vulnerability report from '{input_file}'...")

    try:
        # Read the CSV file. The first few lines of the shared file indicate it's CSV.
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return
    except KeyError:
        print(f"Error: The column '{asset_column}' was not found in the file.")
        print("Please check the column header for 'AssetName' in your report.")
        return
    
    total_rows = len(df)
    print(f"Successfully read {total_rows} records.")
    
    # Apply the categorization logic to create a new 'Category' column
    print("Applying asset name pattern matching to categorize assets...")
    df['Category'] = df[asset_column].apply(get_asset_category)
    
    # Find all unique categories to determine the number of output files
    categories = df['Category'].unique()
    print(f"Identified {len(categories)} unique categories for splitting.")

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Group the DataFrame by the new 'Category' column
    grouped = df.groupby('Category')

    # Iterate through each group and save it to a new Excel file
    for i, (category_name, group_df) in enumerate(grouped, 1):
        # Sanitize the category name to ensure a valid filename
        safe_name = sanitize_filename(category_name)
        output_path = os.path.join(output_dir, f"{safe_name}.xlsx")
        
        # Save the group to an Excel file
        group_df.to_excel(output_path, index=False)
        print(f"  [{i}/{len(categories)}] Saved '{category_name}' with {len(group_df)} rows to '{output_path}'.")

    print("\n✅ Processing complete. Reports are ready to be shared.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python categorize_assets.py <path_to_input_file.csv>")
        sys.exit(1)

    input_file_path = sys.argv[1]
    process_vulnerability_report(input_file_path, ASSET_NAME_COLUMN, OUTPUT_DIRECTORY)
