import os
import threading
from yaml_file_hanlder import YamlFileHandler
from playbook_runner import PlaybookRunner
from time import sleep

# Set environment variable to disable host key checking
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'


def run_ansible_playbook():
    """
    Run Ansible playbooks concurrently using threads.
    Creates a new YamlFileHandler instance for each YAML file.
    """
    yaml_handler = YamlFileHandler()
    spreadsheet_data = yaml_handler.aci_spreadsheet_data[:1]

    if not spreadsheet_data:
        print("🚫 No YAML variable data found for ACI deployment.")
        return

    threads = []
    counter_label = 1
    for data_row in spreadsheet_data:
        # Create a new handler for each file
        file_yaml_handler = YamlFileHandler()

        # Create and persist YAML file for this data_row
        file_yaml_handler.create_aci_yaml_files(data_row)
        file_path = file_yaml_handler.yaml_file_path
        playbook_handler = PlaybookRunner()

        # Set the file name for the ACI YAML file
        epg_pair_in_progress = file_yaml_handler.safe_str(data_row.get("CONTRACT_NAME", "")).removeprefix('CON_')

        # Start a new thread to run the playbook
        thread = threading.Thread(
            target=playbook_handler.run_playbook,
            args=(file_path, epg_pair_in_progress, counter_label)
        )
        thread.start()
        sleep(3)  # Optional sleep to avoid overwhelming the system
        counter_label += 1
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    run_ansible_playbook()

