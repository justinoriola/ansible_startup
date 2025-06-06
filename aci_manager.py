import yaml
import pandas as pd


class AciManager:
    ACI_SPREADSHEET_PATH = "/Users/justin/Desktop/Justin/cisco_sandboxes/Dev_sec_plan/DevSec study plan.xlsx"

    def __init__(self, tenant_name, vrf_name, bridge_domain_name, bridge_domain_ip, l3out, l3out_ext_epg_name):
        self.l3out_status = False
        self.l3out_is_involved = None
        self.l3out_contract_type = None
        self.other_epg_contract_type = None
        self.tenant_name = tenant_name
        self.vrf_name = vrf_name
        self.bridge_domain_name = bridge_domain_name
        self.bridge_domain_ip = bridge_domain_ip
        self.l3out = l3out
        self.l3out_ext_epg = l3out_ext_epg_name
        self.aci_spreadsheet_data = self._load_aci_spreadsheet_data()

    def create_aci_yaml_files(self):
        counter = 0
        for aci_data in self.aci_spreadsheet_data:
            counter += 1

            # Ensure all required fields are present
            self.l3out_is_involved = self.is_l3out_involved(aci_data)
            self.l3out_status = self.l3out_is_involved.get("status", False) if self.l3out_is_involved else False
            self.l3out_contract_type = self.l3out_is_involved.get(
                "l3out_contract_type") if self.l3out_is_involved else False
            self.other_epg_contract_type = self._determine_other_epg_contract_type()

            # Create YAML files for ACI configuration
            formated_spreadsheet_data = self.build_aci_config_payload(aci_data)

            if not formated_spreadsheet_data:
                print("No data available to create YAML files.")
                return

            # Determine the path based on L3Out status
            if self.l3out_status:
                aci_vars_path = f"./vars/aci_vars_l3out_{counter}.yml"
            else:
                aci_vars_path = f"./vars/aci_vars_{counter}.yml"

            # Ensure the directory exists
            import os
            os.makedirs(os.path.dirname(aci_vars_path), exist_ok=True)

            try:
                with open(aci_vars_path, 'w') as file:
                    yaml.dump(formated_spreadsheet_data, file, default_flow_style=False)
                print(f"YAML file created successfully.")
                if counter == 3:
                    break
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
            return data if data else {}
        except FileNotFoundError:
            print("ACI Excel file not found.")
            return {}
        except Exception as e:
            print(f"Unexpected error reading Excel file: {e}")
            return {}

    def is_l3out_involved(self, data_entry):
        # Extract just the consumed and provided EPGs
        epg_entries = dict(list(data_entry.items())[:2])

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

    def build_aci_config_payload(self, aci_spreadsheet):
        """
        Builds a structured ACI config dictionary from spreadsheet input.

        :return: Dictionary formatted for ACI automation.
        """
        REQUIRED_KEYS = [
            'CONSUMED_EPG', 'PROVIDED_EPG', 'CONTRACT_NAME', 'CONTRACT_SCOPE',
            'SUBJECT_NAME', 'VZ_FILTER_NAME', 'VZ_FILTER_ENTRY_NAME',
            'IP_PROTOCOL', 'PORTS_FROM', 'PORTS_TO'
        ]

        # Check if aci is a dictionary and contains the required keys
        if not isinstance(aci_spreadsheet, dict):
            print("Invalid or missing ACI spreadsheet data.")
            return {}

        missing = [k for k in REQUIRED_KEYS if k not in aci_spreadsheet]
        if missing:
            print(f"Missing required keys: {', '.join(missing)}")
            return {}

        safe = AciManager.safe_str  # Shortcut for cleaner lines

        def build_application_profiles():
            try:
                if self.l3out_status:
                    epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                    app_profile = safe(aci_spreadsheet.get(epg_key, ""))

                    # Check prefix before slicing
                    if app_profile.startswith("EPG_"):
                        ap_name = f"AP_{app_profile[4:]}"
                    else:
                        ap_name = f"AP_{app_profile}"

                    return [{"ap": ap_name}]

                else:
                    consumed_epg = safe(aci_spreadsheet.get("CONSUMED_EPG", ""))
                    provided_epg = safe(aci_spreadsheet.get("PROVIDED_EPG", ""))

                    aps = []
                    for epg in [consumed_epg, provided_epg]:
                        if epg:
                            ap_name = f"AP_{epg[4:]}" if epg.startswith("EPG_") else f"AP_{epg}"
                            aps.append({"ap": ap_name})
                    return aps

            except Exception as e:
                print(f"Error building application profiles: {e}")
                return []

        def get_corresponding_ap():
            if self.l3out_status:
                ap = build_application_profiles()[0]['ap']
            else:
                ap = build_application_profiles()[1]['ap'] if self.other_epg_contract_type == "consumer" \
                    else build_application_profiles()[0]['ap']
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
                    create_epg(get_corresponding_ap(), aci_spreadsheet[epg_key])
                )
            else:
                epg_list.append(
                    create_epg(build_application_profiles()[1]['ap'], aci_spreadsheet['PROVIDED_EPG'])
                )
                epg_list.append(
                    create_epg(build_application_profiles()[0]['ap'], aci_spreadsheet['CONSUMED_EPG'])
                )
            return epg_list

        def build_epg_contracts():
            def create_contract(epg, contract_type, ap):
                return {
                    "epg": safe(epg),
                    "scope": safe(aci_spreadsheet["CONTRACT_SCOPE"]),
                    "contract": safe(aci_spreadsheet["CONTRACT_NAME"]),
                    "contract_type": contract_type,
                    "ap": ap,
                }

            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                contract_type = epg_key.lower().removesuffix("d_epg") + "r"
                return [
                    create_contract(
                    epg=aci_spreadsheet[epg_key],
                    contract_type=contract_type,
                    ap=get_corresponding_ap()
                    )
                ]
            else:
                return [
                    create_contract(
                        epg=aci_spreadsheet["PROVIDED_EPG"],
                        contract_type="provider",
                        ap=build_application_profiles()[1]['ap']
                    ),
                    create_contract(
                        epg=aci_spreadsheet["CONSUMED_EPG"],
                        contract_type="consumer",
                        ap=build_application_profiles()[0]['ap']
                    )
                ]

        def build_external_epg():
            if not self.l3out_status:
                return False
            contract_type = self.l3out_contract_type[:-1] + "r"
            return [
                {
                    "l3out_name": safe(self.l3out),
                    "l3out_ext_epg": safe(self.l3out_ext_epg),
                    "contract": safe(aci_spreadsheet["CONTRACT_NAME"]),
                    "contract_type": safe(contract_type)
                }
            ]

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
                "contract": safe(aci_spreadsheet["CONTRACT_NAME"]),
                "scope": safe(aci_spreadsheet["CONTRACT_SCOPE"]),
                "subject": safe(aci_spreadsheet["SUBJECT_NAME"]),
                "filter": safe(aci_spreadsheet["VZ_FILTER_NAME"]),
            }],
            "filters": [{
                "filter": safe(aci_spreadsheet["VZ_FILTER_NAME"]),
                "entry": safe(aci_spreadsheet["VZ_FILTER_ENTRY_NAME"]),
                "protocol": safe(aci_spreadsheet["IP_PROTOCOL"]),
                "port_from": str(int(aci_spreadsheet["PORTS_FROM"])),
                "port_to": str(int(aci_spreadsheet["PORTS_TO"])),
            }],
            "epg_contracts": build_epg_contracts(),
            "external_epg": build_external_epg()
        }

        # Ensure all necessary keys are present in the output data
        return output_data
