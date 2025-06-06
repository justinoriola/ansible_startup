import yaml
import pandas as pd


class AciManager:
    ACI_SPREADSHEET_PATH = "/Users/justin/Desktop/Justin/cisco_sandboxes/Dev_sec_plan/DevSec study plan.xlsx"

    def __init__(self, tenant_name, vrf_name, bridge_domain_name, bridge_domain_ip, l3out, l3out_ext_epg_name):
        self.tenant_name = tenant_name
        self.vrf_name = vrf_name
        self.bridge_domain_name = bridge_domain_name
        self.bridge_domain_ip = bridge_domain_ip
        self.l3out = l3out
        self.l3out_ext_epg = l3out_ext_epg_name
        self.aci_spreadsheet_data = self._load_aci_spreadsheet_data()
        self.l3out_is_involved = self.is_l3out_involved()
        self.l3out_status = self.l3out_is_involved.get("status", False) if self.l3out_is_involved else False
        self.l3out_contract_type = self.l3out_is_involved.get("l3out_contract_type") if self.l3out_is_involved else False
        self.other_epg_contract_type = self._determine_other_epg_contract_type()
        self.ap = []
        self.epgs = []
        self.epg_contracts = []

    def create_aci_yaml_files(self):
        # Create YAML files for ACI configuration
        formated_spreadsheet_data = self.build_aci_config_payload()
        if not formated_spreadsheet_data:
            print("No data available to create YAML files.")
            return

        # Determine the path based on L3Out status
        if self.l3out_status:
            aci_vars_path = f"./vars/aci_vars_l3out.yml"
        else:
            aci_vars_path = f"./vars/aci_vars.yml"

        # Ensure the directory exists
        import os
        os.makedirs(os.path.dirname(aci_vars_path), exist_ok=True)

        try:
            with open(aci_vars_path, 'w') as file:
                yaml.dump(formated_spreadsheet_data, file, default_flow_style=False)
            print(f"YAML file created successfully.")
        except Exception as e:
            print(f"Error creating YAML files: {e}")

    @staticmethod
    def safe_str(value):
        """Utility to safely convert values to string, handling NaN and None."""
        import math
        return "" if value is None or (isinstance(value, float) and math.isnan(value)) else str(value)

    def _load_aci_spreadsheet_data(self):
        try:
            df = pd.read_excel(AciManager.ACI_SPREADSHEET_PATH, sheet_name='Sheet1')
            data = df.to_dict(orient='records')
            return data[-1] if data else {}
        except FileNotFoundError:
            print("ACI Excel file not found.")
            return {}
        except Exception as e:
            print(f"Unexpected error reading Excel file: {e}")
            return {}

    def is_l3out_involved(self):
        # Extract just the consumed and provided EPGs
        epg_entries = dict(list(self.aci_spreadsheet_data.items())[:2])

        _is_l3out_involved = False

        for key, value in epg_entries.items():
            if value == 'EPG_L3OUT':
                _is_l3out_involved = True
                return {
                    "status": _is_l3out_involved,
                    "l3out_contract_type": key.split('_')[0].lower()
                }

    def _determine_other_epg_contract_type(self):
        """Determine the contract type for the other EPG."""
        if self.l3out_status and self.l3out_contract_type == "consumed":
            return "provided"
        return "consumed"

    def build_aci_config_payload(self):
        """
        Builds a structured ACI config dictionary from spreadsheet input.

        :return: Dictionary formatted for ACI automation.
        """
        REQUIRED_KEYS = [
            'CONSUMED_EPG', 'PROVIDED_EPG', 'CONTRACT_NAME', 'CONTRACT_SCOPE',
            'SUBJECT_NAME', 'VZ_FILTER_NAME', 'VZ_FILTER_ENTRY_NAME',
            'IP_PROTOCOL', 'PORTS_FROM', 'PORTS_TO'
        ]

        if not isinstance(self.aci_spreadsheet_data, dict):
            print("Invalid or missing ACI spreadsheet data.")
            return {}

        aci = self.aci_spreadsheet_data
        missing = [k for k in REQUIRED_KEYS if k not in aci]
        if missing:
            print(f"Missing required keys: {', '.join(missing)}")
            return {}

        safe = AciManager.safe_str  # Shortcut for cleaner lines

        def build_application_profiles():
            try:
                if self.l3out_status:
                    epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                    app_profile = safe(aci.get(epg_key, ""))

                    # Check prefix before slicing
                    if app_profile.startswith("EPG_"):
                        ap_name = f"AP_{app_profile[4:]}"
                    else:
                        ap_name = f"AP_{app_profile}"

                    self.ap.append({"ap": ap_name})

                else:
                    consumed_epg = safe(aci.get("CONSUMED_EPG", ""))
                    provided_epg = safe(aci.get("PROVIDED_EPG", ""))

                    # aps = []
                    for epg in [consumed_epg, provided_epg]:
                        if epg:
                            ap_name = f"AP_{epg[4:]}" if epg.startswith("EPG_") else f"AP_{epg}"
                            self.ap.append({"ap": ap_name})
                return self.ap

            except Exception as e:
                print(f"Error building application profiles: {e}")
                return []

        def get_corresponding_ap():
            if self.l3out_status:
                ap = self.ap[0]['ap']
            else:
                ap = self.ap[0]['ap'] if self.other_epg_contract_type == "consumer" \
                    else self.ap[1]['ap']
            return ap

        def build_endpoint_groups():
            epg_list = []

            def create_epg(ap, epg_name):
                return {
                    "ap": ap,
                    "epg": safe(epg_name),
                    "bd": safe(self.bridge_domain_name),
                    "encap": "22"
                }

            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                epg_list.append(
                    create_epg(get_corresponding_ap(), aci[epg_key])
                )
            else:
                epg_list.append(
                    create_epg(self.ap[1]['ap'], aci['PROVIDED_EPG'])
                )
                epg_list.append(
                    create_epg(self.ap[0]['ap'], aci['CONSUMED_EPG'])
                )

            self.epgs.extend(epg_list)

        def build_epg_contracts():
            def create_contract(epg, contract_type, ap):
                return {
                    "epg": safe(epg),
                    "scope": safe(aci["CONTRACT_SCOPE"]),
                    "contract": safe(aci["CONTRACT_NAME"]),
                    "contract_type": contract_type,
                    "ap": ap,
                }

            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                contract = create_contract(
                    epg=aci[epg_key],
                    contract_type=self.other_epg_contract_type,
                    ap=get_corresponding_ap()
                )
                self.epg_contracts.append(contract)
            else:
                self.epg_contracts.extend([
                    create_contract(
                        epg=aci["PROVIDED_EPG"],
                        contract_type="provider",
                        ap=self.ap[1]['ap']
                    ),
                    create_contract(
                        epg=aci["CONSUMED_EPG"],
                        contract_type="consumer",
                        ap=self.ap[0]['ap']
                    )
                ])


        def build_external_epg():
            if not self.l3out_status:
                return False
            return [
                {
                    "l3out_name": safe(self.l3out),
                    "l3out_ext_epg": safe(self.l3out_ext_epg),
                    "contract": safe(aci["CONTRACT_NAME"]),
                    "contract_type": safe(self.l3out_contract_type)
                }
            ]

        # Build the application profiles, endpoint groups, and other components
        build_application_profiles()
        build_endpoint_groups()
        build_epg_contracts()

        # Check if any of the lists are empty and return early if so
        if not self.ap or not self.epgs or not self.epg_contracts:
            print("No valid application profiles, endpoint groups, or contracts found.")
            return {}

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
            "aps": self.ap,
            "epgs": self.epgs,
            "contracts": [{
                "contract": safe(aci["CONTRACT_NAME"]),
                "scope": safe(aci["CONTRACT_SCOPE"]),
                "subject": safe(aci["SUBJECT_NAME"]),
                "filter": safe(aci["VZ_FILTER_NAME"]),
            }],
            "filters": [{
                "filter": safe(aci["VZ_FILTER_NAME"]),
                "entry": safe(aci["VZ_FILTER_ENTRY_NAME"]),
                "protocol": safe(aci["IP_PROTOCOL"]),
                "port_from": str(int(aci["PORTS_FROM"])),
                "port_to": str(int(aci["PORTS_TO"])),
            }],
            "epg_contracts": self.epg_contracts,
            "external_epg": build_external_epg()
        }

        return output_data
