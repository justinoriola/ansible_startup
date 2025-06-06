
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
    """
    vars_dir = './vars'
    yml_files = [file for file in os.listdir(vars_dir) if file.startswith('aci_vars_') and file.endswith('.yml')]

    if not yml_files:
        print("No YAML files found in the 'vars' directory.")
        return

    for file_name in yml_files:
        full_path = os.path.join(vars_dir, file_name)
        print(f"Running playbook with vars file: {full_path}")
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i", "inventory",
                "./cisco_aci/05_aci_deploy_app.yml",
                "-e", f"@{full_path}",
            ],
            capture_output=True,
            text=True
        )

        # Check if the playbook ran successfully
        play_recap_started = False
        for line in result.stdout.splitlines():
            if "PLAY RECAP" in line:
                play_recap_started = True
            if play_recap_started:
                print(line)


if __name__ == "__main__":
    run_ansible_playbook()