import os
import yaml
import pandas as pd
import json
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
        self.l3out_status = self.l3out_is_involved.get("status", False)
        self.l3out_contract_type = self.l3out_is_involved.get("l3out_contract_type")
        self.other_epg_contract_type = self._determine_other_epg_contract_type()

    def create_aci_yaml_files(self):
        # Create YAML files for ACI configuration
        formated_spreadsheet_data = self.build_aci_config_payload()
        if not formated_spreadsheet_data:
            print("No data available to create YAML files.")
            return

        try:
            with open(f"./yaml_folder/epg.yaml", 'w') as file:
                yaml.dump({"epg": formated_spreadsheet_data}, file)
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
            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                return [{
                    "tenant": safe(self.tenant_name),
                    "ap": f"AP_{safe(aci[epg_key])}",
                }]
            else:
                return [
                    {
                        "tenant": safe(self.tenant_name),
                        "ap": f"AP_{safe(aci['CONSUMED_EPG'])}",
                    },
                    {
                        "tenant": safe(self.tenant_name),
                        "ap": f"AP_{safe(aci['PROVIDED_EPG'])}",
                    }
                ]

        def build_endpoint_groups():
            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                return [
                    {
                        "tenant": safe(self.tenant_name),
                        "ap": f"AP_{safe(aci[epg_key])}",
                        "epg": safe(aci[epg_key]),
                        "bd": safe(self.bridge_domain_name),
                        "encap": "22"
                    },
                    {
                        "tenant": safe(self.tenant_name),
                        "l3out_name": safe(self.l3out),
                        "l3out_ext_epg": safe(self.l3out_ext_epg)
                    }
                ]
            else:
                return [
                    {
                        "tenant": safe(self.tenant_name),
                        "ap": f"AP_{safe(aci['CONSUMED_EPG'])}",
                        "epg": safe(aci['CONSUMED_EPG']),
                        "bd": safe(self.bridge_domain_name),
                        "encap": "22",
                    },
                    {
                        "tenant": safe(self.tenant_name),
                        "ap": f"AP_{safe(aci['PROVIDED_EPG'])}",
                        "epg": safe(aci['PROVIDED_EPG']),
                        "bd": safe(self.bridge_domain_name),
                        "encap": "22",
                    }
                ]

        def build_epg_contracts():
            if self.l3out_status:
                epg_key = f"{self.other_epg_contract_type.upper()}_EPG"
                return [
                    {
                        "tenant": safe(self.tenant_name),
                        "epg": safe(aci[epg_key]),
                        "scope": safe(aci["CONTRACT_SCOPE"]),
                        "contract": safe(aci["CONTRACT_NAME"]),
                        "contract_type": self.other_epg_contract_type,
                    },
                    {
                        "tenant": safe(self.tenant_name),
                        "contract": safe(aci["CONTRACT_NAME"]),
                        "contract_type": safe(self.l3out_contract_type),
                        "l3out_name": safe(self.l3out),
                        "l3out_ext_epg": safe(self.l3out_ext_epg)
                    }
                ]
            else:
                return [
                    {
                        "tenant": safe(self.tenant_name),
                        "epg": safe(aci["CONSUMED_EPG"]),
                        "scope": safe(aci["CONTRACT_SCOPE"]),
                        "contract": safe(aci["CONTRACT_NAME"]),
                        "contract_type": "consumed",
                    },
                    {
                        "tenant": safe(self.tenant_name),
                        "epg": safe(aci["PROVIDED_EPG"]),
                        "scope": safe(aci["CONTRACT_SCOPE"]),
                        "contract": safe(aci["CONTRACT_NAME"]),
                        "contract_type": "provided",
                    }
                ]

        def build_external_epg():
            if not self.l3out_status:
                return None
            return {
                "tenant": safe(self.tenant_name),
                "l3out_name": safe(self.l3out),
                "l3out_ext_epg": safe(self.l3out_ext_epg),
                "contract": safe(aci["CONTRACT_NAME"]),
                "contract_type": safe(aci[f"{self.other_epg_contract_type.upper()}_EPG"])
            }

        output_data = {
            "tenant": self.tenant_name,
            "vrf": self.vrf_name,
            "bridge_domain": [{
                "bd": safe(self.bridge_domain_name),
                "gateway": safe(self.bridge_domain_ip),
                "mask": "24",
                "scope": "public",
            }],
            "ap": build_application_profiles(),
            "epgs": build_endpoint_groups(),
            "contracts": [{
                "tenant": safe(self.tenant_name),
                "contract": safe(aci["CONTRACT_NAME"]),
                "scope": safe(aci["CONTRACT_SCOPE"]),
                "subject": safe(aci["SUBJECT_NAME"]),
                "filter": safe(aci["VZ_FILTER_NAME"]),
            }],
            "filters": [{
                "tenant": safe(self.tenant_name),
                "filter": safe(aci["VZ_FILTER_NAME"]),
                "entry": safe(aci["VZ_FILTER_ENTRY_NAME"]),
                "protocol": safe(aci["IP_PROTOCOL"]),
                "port_from": str(int(aci["PORTS_FROM"])),
                "port_to": str(int(aci["PORTS_TO"])),
            }],
            "epg_contracts": build_epg_contracts(),
            "external_epg": build_external_epg()
        }

        return output_data

