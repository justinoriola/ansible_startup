
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


import os
import subprocess
import threading

def run_playbook(file_name):
    """
    Run a single Ansible playbook with the given YAML variable file.
    """
    try:
        print(f"\n📢 Starting Ansible for: {file_name}...")
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i", "inventory",
                "./cisco_aci/05_aci_deploy_app.yml",
                "-e", f"@./vars/{file_name}",
            ],
            capture_output=True,
            text=True
        )

        # print(f"\n===== [OUTPUT for {file_name}] =====")
        # print(result.stdout)
        #
        # print(f"\n===== [ERROR for {file_name}] =====")
        # print(result.stderr)

        # Optional: Print just the PLAY RECAP section
        recap_line = next((line for line in result.stdout.splitlines() if line.strip().startswith("sandboxapicdc.cisco.com")), None)
        if recap_line:
            print(f"\n[RECAP for {file_name}]: {recap_line}")

    except Exception as e:
        print(f"[Exception while running playbook for {file_name}]: {e}")

def run_ansible_playbook():
    """
    Run Ansible playbooks concurrently using threads.
    """
    yml_files = [file for file in os.listdir('./vars') if file.startswith('aci_vars_') and file.endswith('.yml')]
    if not yml_files:
        print("No YAML files found in the 'vars' directory.")
        return

    threads = []

    for file_name in yml_files:
        thread = threading.Thread(target=run_playbook, args=(file_name,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Wait for all threads to finish

    print("\n✅ Playbook Completed Successfully.")


if __name__ == "__main__":
    run_ansible_playbook()

