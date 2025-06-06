
import subprocess
import os
from aci_manager import AciManager

# Set environment variable to disable host key checking
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'

# Define AciManager instance
aci = AciManager(
    'TN_Test',
    'prod_legacy',
    'prod_tn',
    '192.168.0.1',
    'l3Out',
    'EXT_EPG_INTERNET'
)

# Create the necessary ACI YAML files
aci.create_aci_yaml_files()


def run_ansible_playbook():
    """
    Run the Ansible playbook to deploy the application in Cisco ACI.
    :return:
    """
    # Ensure the inventory file exists
    if aci.l3out_status:
        vars_file = "./vars/aci_vars_l3out.yml"
    else:
        vars_file = "./vars/aci_vars.yml"

    # Run the Ansible playbook with the specified inventory and variables file
    result = subprocess.run(
        [
            "ansible-playbook",
            "-i", "inventory",
            "./cisco_aci/05_aci_deploy_app.yml",
            "-e", f"@{vars_file}"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)


if __name__ == "__main__":
    run_ansible_playbook()