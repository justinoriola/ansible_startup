import math
import yaml
import pandas as pd
import os
import shutil


class FileHandler:
    """
    Handles:
    - Reading ACI spreadsheet data
    - Transforming spreadsheet rows into structured ACI payloads
    - Writing YAML configuration files
    - Updating spreadsheet data with deduplication and backup

    This class acts as the bridge between raw Excel input and ACI-ready config output.

    Required __init__ attributes (must be defined for correct operation):
    - aci_spreadsheet_directory  # Path to source Excel file
    - yaml_file_path             # Base output path for generated YAML files
    - tenant_name                # ACI tenant name
    - vrf_name                   # ACI VRF name
    - bridge_domain_name         # Bridge Domain name
    - bridge_domain_ip           # Bridge Domain gateway IP
    - l3out                      # L3OUT name
    - l3out_ext_epg              # External EPG name for L3OUT
    """

    def __init__(self, **kwargs):

        self.l3out_status = False
        self.is_l3out = None
        self.other_epg_contract = None
        self.l3out_contract = None
        self.other_epg_contract_type = None
        self.aci_spreadsheet_directory = kwargs.get('aci_spreadsheet_directory') or "./data/DevSec_study_plan.xlsx"
        self.yaml_file_path = "vars/aci_config_"
        self.tenant_name = kwargs.get('tenant_name') or "TN_Default"
        self.vrf_name = kwargs.get('vrf_name') or "VRF_Default"
        self.bridge_domain_name = kwargs.get('bridge_domain_name') or "BD_Default"
        self.bridge_domain_ip = kwargs.get('bridge_domain_ipe') or "192.168.0.1"
        self.l3out = kwargs.get('l3out') or "L3OUT_Default"
        self.l3out_ext_epg = kwargs.get('l3out_ext_epg') or "EXT_EPG_Default"

        # Load spreadsheet data into memory at initialization
        self.aci_spreadsheet_data = self._load_aci_spreadsheet_data()

    # === Beginning of Static utility methods ===
    @staticmethod
    def safe_str(value):
        """
        Safely converts values to string.
        Handles: - None, NaN / NaT (from pandas)
        Returns empty string for invalid values.
        """
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return str(value)

    @staticmethod
    def is_l3out_in_epg(aci_spreadsheet_row):
        """
        Determines whether L3OUT is involved in the record.

        Returns:
        {
            "status": bool,
            "other_epg_contract": str | None   # the EPG that is NOT L3OUT
        }
        """
        consumed_epg = (aci_spreadsheet_row.get("CONSUMED_EPG") or "").lower()
        provided_epg = (aci_spreadsheet_row.get("PROVIDED_EPG") or "").lower()

        is_consumed_l3 = "l3_out" in consumed_epg
        is_provided_l3 = "l3_out" in provided_epg

        # If neither contains L3OUT
        if not (is_consumed_l3 or is_provided_l3):
            return {"status": False, "other_epg_contract": None, "l3out_contract": None}

        # Determine the non-L3OUT EPG
        if is_consumed_l3 and not is_provided_l3:
            other_epg = provided_epg
            l3_out = consumed_epg
        elif is_provided_l3 and not is_consumed_l3:
            other_epg = consumed_epg
            l3_out = provided_epg
        else:
            # Edge case: both contain L3OUT (unlikely but safe handling)
            other_epg = None
            l3_out = None

        return {"status": True, "other_epg_contract": other_epg, "l3out_contract": l3_out}

    # === End of static utility methods ===

    def _load_aci_spreadsheet_data(self):
        """
        Loads Excel spreadsheet data into memory.
        Returns: - List of dicts (each row = one record) filtered by STATUS == "Done" or empty list on failure
        """
        try:
            df = pd.read_excel(self.aci_spreadsheet_directory, sheet_name='ACI_CONTRACTS', engine='openpyxl')
            data = df.to_dict(orient='records')

            # Filter only rows where STATUS != "Done"
            rows_with_not_done_status = [row for row in data if str(row.get("STATUS")).strip().lower() != "done"]

            # Return all matching rows as a list (or empty list if none found)
            return rows_with_not_done_status if rows_with_not_done_status else []
        except FileNotFoundError:
            print("ACI Excel file not found.")
            return []
        except Exception as e:
            print(f"Unexpected error reading Excel file: {e}")
            return []

    def create_aci_yaml_files(self, aci_spreadsheet_row):
        """
        Processes a single spreadsheet row and generates a YAML config file.

        Steps:
        1. Detect L3OUT involvement
        2. Determine contract direction
        3. Build structured payload
        4. Write YAML file
        """

        # Build ACI payload structure
        formatted_payload = self.build_aci_config_payload(aci_spreadsheet_row)

        if not formatted_payload:
            print("No data available to create YAML files.")
            return

        # Generate unique YAML filename based on object instance
        yaml_file_name = str(self).split()[-1].strip(">")
        self.yaml_file_path += f"{yaml_file_name}.yml"

        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.yaml_file_path), exist_ok=True)

        try:
            with open(self.yaml_file_path, 'w') as file:
                yaml.dump(formatted_payload, file, default_flow_style=False)
            print(f"YAML file created successfully - {self.yaml_file_path}.")
        except Exception as e:
            print(f"Error creating YAML files: {e}")

    def build_aci_config_payload(self, aci_spreadsheet_row):
        """
        Core transformation logic.

        Converts a spreadsheet row into structured ACI configuration.

        Output includes:
        - tenant, vrf
        - bridge domains
        - application profiles (APs)
        - endpoint groups (EPGs)
        - contracts and filters
        - EPG contract bindings
        - external EPG (if L3OUT involved)
        """
        required_keys = [
            'CONSUMED_EPG', 'PROVIDED_EPG', 'CONTRACT_NAME', 'CONTRACT_SCOPE',
            'SUBJECT_NAME', 'VZ_FILTER_NAME', 'VZ_FILTER_ENTRY_NAME',
            'IP_PROTOCOL', 'PORTS_FROM', 'PORTS_TO'
        ]

        safe = FileHandler.safe_str  # Shortcut for cleaner lines

        # Check if aci is a dictionary and contains the required keys
        if not isinstance(aci_spreadsheet_row, dict):
            print("Invalid or missing ACI spreadsheet data.")
            return {}

        missing = [k for k in required_keys if k not in aci_spreadsheet_row]
        if missing:
            print(f"Missing required keys: {', '.join(missing)}")
            return {}

        # Detect if L3OUT is part of this record
        l3out_info = FileHandler.is_l3out_in_epg(aci_spreadsheet_row)
        self.l3out_status = l3out_info["status"]
        self.other_epg_contract = l3out_info["other_epg_contract"]
        self.l3out_contract = l3out_info["l3out_contract"]

        # == Unpack aci_spreadsheet_row values with safety ==
        consumed_epg = safe(aci_spreadsheet_row.get("CONSUMED_EPG"))
        provided_epg = safe(aci_spreadsheet_row.get("PROVIDED_EPG"))
        contract_scope = safe(aci_spreadsheet_row.get("CONTRACT_SCOPE"))
        contract_name = safe(aci_spreadsheet_row.get("CONTRACT_NAME"))
        subject_name = safe(aci_spreadsheet_row.get("SUBJECT_NAME"))
        filter_name = safe(aci_spreadsheet_row.get("VZ_FILTER_NAME"))
        filter_entry_name = safe(aci_spreadsheet_row.get("VZ_FILTER_ENTRY_NAME"))
        ip_protocol = safe(aci_spreadsheet_row.get("IP_PROTOCOL"))
        ports_from = safe(aci_spreadsheet_row.get("PORTS_FROM"))
        ports_to = safe(aci_spreadsheet_row.get("PORTS_TO"))

        def build_application_profiles():
            """
            Builds Application Profiles (APs) from EPG names.
            Rule:
            EPG_X -> AP_X
            """
            try:
                def format_ap(epg):
                    epg = safe(epg)
                    return f"AP_{epg[4:]}" if epg.startswith("EPG_") else f"AP_{epg}"

                # == If L3OUT is involved, we only create the AP for the non-L3OUT EPG ==
                if self.l3out_status:
                    return [{"ap": format_ap(self.other_epg_contract)}]  # create AP for the non-L3OUT EPG only

                return [{"ap": format_ap(epg)} for epg in (consumed_epg, provided_epg) if epg]

            except Exception as e:
                print(f"Error building application profiles: {e}")
                return []

        def get_corresponding_ap():
            """
            Returns correct AP based on contract direction logic.
            """
            aps = build_application_profiles()
            if not aps:
                return None

        def build_endpoint_groups():
            """
            Builds endpoint group (EPG) definitions.
            """

            def create_epg(ap, epg_name):
                return {
                    "ap": ap,
                    "epg": safe(epg_name),
                    "bd": safe(self.bridge_domain_name),
                    "encap": "22"
                }

            aps = build_application_profiles()
            provided_ap = aps[1]['ap']
            consumed_ap = aps[0]['ap']

            # == If L3OUT is involved, we only create the EPG for the non-L3OUT side ==
            if self.l3out_status:
                return [create_epg(get_corresponding_ap(), self.other_epg_contract)]

            return [
                create_epg(provided_ap, provided_epg),
                create_epg(consumed_ap, consumed_epg),
            ]

        def build_epg_contracts():
            """
            Maps EPGs to contracts (provider/consumer roles).
            """
            # == Get APs for the EPGs ==
            aps = build_application_profiles()
            provided_ap = aps[1]['ap']
            consumed_ap = aps[0]['ap']

            def create_contract(epg, contract_type, ap):
                return {
                    "epg": safe(epg),
                    "scope": contract_scope,
                    "contract": contract_name,
                    "contract_type": contract_type[:-1] + "r",
                    "ap": ap,
                }

            # == If L3OUT is involved, we only create the contract for the non-L3OUT EPG ==
            if self.l3out_status:
                contract_type = self.other_epg_contract
                return [create_contract(contract_type, contract_type, get_corresponding_ap())]

            return [
                create_contract(provided_epg, "provider", provided_ap),
                create_contract(consumed_epg, "consumer", consumed_ap)
            ]

        def build_external_epg():
            """
            Builds external EPG configuration when L3OUT is involved.
            """
            if not self.l3out_status:
                return False
            return [{
                "l3out_name": safe(self.l3out),
                "l3out_ext_epg": safe(self.l3out_ext_epg),
                "contract": contract_name,
                "contract_type": self.l3out_contract[:-1] + "r"
            }]

        # Prepare the output data structure
        output_data = {
            "tenant": self.tenant_name,
            "vrf": self.vrf_name,
            "bridge_domains": [{
                "bd": safe(self.bridge_domain_name),
                "gateway": safe(self.bridge_domain_ip),
                "mask": "24",
                "scope": "public",
            }],
            "aps": build_application_profiles(),
            "epgs": build_endpoint_groups(),
            "contracts": [{
                "contract": contract_name,
                "scope": contract_scope,
                "subject": subject_name,
                "filter": filter_name,
            }],
            "filters": [{
                "filter": filter_name,
                "entry": filter_entry_name,
                "protocol": ip_protocol,
                "port_from": str(int(ports_from)),
                "port_to": str(int(ports_to)),
            }],
            "epg_contracts": build_epg_contracts(),
            "external_epg": build_external_epg()
        }

        # Ensure all necessary keys are present in the output data
        print("aci config payload built successfully.")
        return output_data

    def update_spreadsheet_data(self, new_data):
        """
        Updates spreadsheet data with deduplication and backup protection.

        Features:
        - Accepts dict or list of dicts
        - Prevents duplicate entries
        - Creates backup if missing
        - Refreshes backup after update
        """
        # === Validate and normalize input ===
        if not new_data:
            print("⚠️ No data provided to update.")
            return

        if isinstance(new_data, dict):
            new_data = [new_data]

        if not isinstance(new_data, list) or not all(isinstance(item, dict) for item in new_data):
            print("⛔️ New data must be a dictionary or a list of dictionaries.")
            return

        # === Ensure in-memory store is initialized ===
        if not hasattr(self, 'aci_spreadsheet_data') or not isinstance(self.aci_spreadsheet_data, list):
            self.aci_spreadsheet_data = []

        # === File paths ===
        output_path = self.aci_spreadsheet_directory
        backup_path = output_path.replace('.xlsx', '_backup.xlsx')

        # === If backup doesn't exist, create it before updating ===
        if not os.path.exists(backup_path):
            if os.path.exists(output_path):
                try:
                    shutil.copyfile(output_path, backup_path)
                    # print(f"🛡️ Backup created before update at: {backup_path}")
                except Exception as e:
                    print(f"⛔️ Failed to create backup: {e}")
                    return
            else:
                print("⚠️ No existing spreadsheet found to back up.")

        # Normalize values to ensure accurate comparison
        def normalize(value):
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return ''
            return str(value).strip()

        # Generate unique signature for each row (used for deduplication)
        def to_row_signature(entry):
            keys = [
                "CONSUMED_EPG", "PROVIDED_EPG", "CONTRACT_NAME", "SUBJECT_NAME",
                "VZ_FILTER_NAME", "IP_PROTOCOL", "PORTS_FROM", "PORTS_TO", "ACTION"
            ]
            return tuple(normalize(entry.get(k)) for k in keys)

        # Filter out records that already exist
        existing_signatures = {to_row_signature(item) for item in self.aci_spreadsheet_data}
        filtered_new_data = [item for item in new_data if to_row_signature(item) not in existing_signatures]

        if not filtered_new_data:
            # print("ℹ️ No new unique data to update. All entries already exist.")
            return

        # Append only new unique records
        self.aci_spreadsheet_data.extend(filtered_new_data)

        # Persist updated data back to Excel
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            df = pd.DataFrame(self.aci_spreadsheet_data)

            # Save updated Excel file
            df.to_excel(output_path, index=False, sheet_name='ACI_CONTRACTS', engine='openpyxl')
            print(f"✅ Spreadsheet updated with {len(filtered_new_data)} new record(s).")

            # Refresh backup after successful update
            shutil.copyfile(output_path, backup_path)
            print(f"🔁 Backup refreshed at: {backup_path}")

        except Exception as e:
            print(f"⛔️ Error saving updated spreadsheet: {e}")
