"""
HR Import module for processing and transforming HR data files.

Functionality:
- Converts names and email addresses to lowercase for system consistency
- Splits tenant-specific users (e.g., Joby Germany) into separate CSV files
- Adds tenantmember column for auto-enrollment in tenant systems
- Supports both Job Assignments and Users file formats via name detection

Usage:
    python HRImport.py [optional tenant_id ...]
    Then enter CSV filenames to process (enter 'q' to quit)
"""
import json
import sys
from pathlib import Path

import pandas

class HRImport:
    """
    Class to represent the HR import process. It takes a filename as input and performs the necessary transformations to ensure that all names are in lowercase and that Joby Germany users are split into a separate file with a tenantmember column for auto enrollment.
    """

    def __init__(self, filename: str) -> None:
        """
        Initialize the HRImport class and load data from CSV file.
        
        Reads the CSV file into a pandas DataFrame for in-memory processing.
        If file read fails, prints error and returns gracefully.

        @param filename: Path to the CSV file to process
        """

        self.filename = filename
        try:
            self.data = pandas.read_csv(filename)
        except Exception as e:
            print(f"Error reading file: {e}")
            return


    def _split_tenant(self, business_unit_description: str, tenant_id: str) -> pandas.DataFrame:
        """
        Split tenant-specific users from the main data file.
        
        Extracts rows matching the given business unit description and writes them to a separate CSV file
        with a tenantmember column appended (for auto-enrollment). Returns the remaining rows to update the
        main data file.

        @param business_unit_description: The business unit to filter on (e.g., "joby germany gmbh")
        @param tenant_id: The tenant ID to assign to split records and use in output filename (e.g., "jbg")
        @return: DataFrame with the matching business unit records removed, ready to replace self.data
        """

        # Create boolean mask: True where business unit matches (case-insensitive comparison)
        # .str.strip() removes whitespace, .str.lower() normalizes case for comparison
        germany_mask = self.data["business unit description"].str.strip().str.lower() == business_unit_description.lower()
        
        # Extract rows matching the mask into separate dataframe for the tenant-specific file
        germany_data = self.data[germany_mask].copy()
        
        # Keep rows that DON'T match the mask (inverted with ~) for the main file
        remaining_data = self.data[~germany_mask]
        
        # If matching records found, write tenant-specific file with tenantmember identifier for auto-enrollment
        if not germany_data.empty:
            germany_filename = self.filename.replace(".csv", f"_{tenant_id}.csv")
            germany_data["tenantmember"] = tenant_id
            germany_data.to_csv(germany_filename)
        
        return remaining_data
    

    def run(self, tenants: list[dict[str, str]]) -> None:
        """
        Orchestrate the transformation pipeline for the loaded CSV file.
        
        Routes to the appropriate processor (_job_assignments or _users) based on filename,
        applies tenant-specific transformations, and writes the result back to the source file.

        @param tenants: List of tenant configurations with business_unit_description and tenant_id
        @raises ValueError: If filename doesn't contain identifying keywords for file type
        """

        print("...working...")

        # Route to appropriate processing method based on filename keyword (case-insensitive check)
        # This allows flexible naming while ensuring correct transformation logic is applied
        if "job assignments" in self.filename.lower():
            self._job_assignments(tenants)
        elif "users" in self.filename.lower():
            self._users(tenants)
        else:
            raise ValueError("Filename must contain either 'Job Assignments' or 'Users' to determine the type of file being processed.")

        # Write transformed data back to the original file
        self.data.to_csv(self.filename)

        # Print success message only after potentially long-running operations complete
        print("Success!")

        return


    def _job_assignments(self, tenants: list[dict[str, str]]) -> None:
        """
        Perform the necessary transformations for the Job Assignments file.
        
        - Removes records with missing/empty useridnumber
        - Splits tenant-specific records into separate files per tenant
        - Normalizes email addresses to lowercase
        """

        # Remove rows where useridnumber is missing (NaN) or empty string to avoid invalid records
        self.data = self.data[~(self.data["useridnumber"].isna() | (self.data["useridnumber"] == ""))]
        
        # Iteratively split tenant-specific records: match on business_unit_description,
        # extract to separate file, update self.data to exclude those rows
        for tenant in tenants:
            self.data = self._split_tenant(tenant["business_unit_description"], tenant["tenant_id"])
        
        # Replace NaN values in Manager email with placeholder string for downstream CSV processing
        # (NaN converts to "nan" in CSV, "#N/A" is a clearer marker for missing values)
        self.data["Manager email"] = self.data["Manager email"].fillna("#N/A")
        
        # Normalize email addresses and user IDs to lowercase for consistent matching in downstream systems
        for name_index in self.data.index:
            self.data.loc[name_index, "Manager email"] = self.data["Manager email"][name_index].lower()
            self.data.loc[name_index, "useridnumber"] = self.data["useridnumber"][name_index].lower()

        return

    def _users(self, tenants: list[dict[str, str]]) -> None:
        """
        Perform the necessary transformations for the Users file.
        
        - Removes records with missing/empty idnumber
        - Splits tenant-specific records into separate files per tenant
        - Normalizes email addresses and IDs to lowercase
        """
        # Remove rows where idnumber is missing (NaN) or empty string to avoid invalid records
        self.data = self.data[~(self.data["idnumber"].isna() | (self.data["idnumber"] == ""))]
        
        # Iteratively split tenant-specific records: match on business_unit_description,
        # extract to separate file, update self.data to exclude those rows
        for tenant in tenants:
            self.data = self._split_tenant(tenant["business_unit_description"], tenant["tenant_id"])
        
        # Normalize email addresses and user IDs to lowercase for consistent matching in downstream systems
        for name_index in self.data.index:
            self.data.loc[name_index, "idnumber"] = self.data["idnumber"][name_index].lower()
            self.data.loc[name_index, "email"] = self.data["email"][name_index].lower()

        return
    

def load_tenants() -> list[dict[str, str]]:
    """
    Load and validate tenant objects from tenants.json located in the same directory as this script.
    
    @return: List of tenant dictionaries with normalized tenant_id (lowercase) and configuration
    @raises FileNotFoundError: If tenants.json cannot be found in the script directory
    """
    # Construct path to tenants.json relative to this script (not current working directory)
    config_path = Path(__file__).resolve().parent / "tenants.json"
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"tenants.json not found at {config_path}")

    # Extract the tenants array from config, defaulting to empty list if missing
    tenants = config.get("tenants", [])
    
    # Build normalized tenant list: filter out any tenants without a tenant_id,
    # convert tenant_id to lowercase for case-insensitive matching in CLI args
    return [
        {
            "tenant_id": tenant.get("tenant_id", "").lower(),
            "business_unit_description": tenant.get("business_unit_description", ""),
            "tenant_name": tenant.get("tenant_name", ""),
        }
        for tenant in tenants
        if tenant.get("tenant_id")  # Only include tenants with a non-empty tenant_id
    ]


def main() -> None:
    """
    Main entry point: loads tenants, validates CLI arguments, then repeatedly prompts for CSV filenames.
    
    CLI Usage:
        python HRImport.py [tenant_id ...]  (optional tenant IDs to filter)
        Then enter CSV filenames to process (enter 'q' to quit)
    
    If tenant_id(s) provided: only those tenants are used for splitting.
    If no tenant_id(s) provided: no tenants are used.
    """
    
    # Load all available tenants from configuration file
    tenants = load_tenants()
    use_tenants: list[dict[str, str]] = []
    
    # Parse CLI arguments to select specific tenants for processing
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            # Normalize argument to lowercase for case-insensitive matching against tenant_id
            normalized_arg = arg.lower()
            
            # Search for tenant(s) matching the provided ID (supports ID filtering/validation)
            matches = [tenant for tenant in tenants if tenant["tenant_id"] == normalized_arg]
            
            # If tenant ID found, add all matching configurations; otherwise raise error
            if matches:
                for tenant in matches:
                    use_tenants.append(tenant)
            else:
                raise ValueError(f"Tenant ID '{arg}' not found")

    # Get filename through stdin, removing surrounding quotes if present
    # Users often copy filenames with quotes from file explorer; strip them for clean paths
    filename = input().strip('"').strip("'")

    # Loop until user enters 'q' to quit, processing each CSV file with the selected tenants
    while (filename != 'q'):
        hr_import = HRImport(filename)
        hr_import.run(use_tenants)
        filename = input().strip('"').strip("'")


if __name__ == "__main__":
    main()