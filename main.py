import os
from yaml_file_handler import YamlFileHandler
from playbook_handler import PlaybookHandler

# Set environment variable to disable host key checking
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'

# Initialize the YAML file handler to read the spreadsheet data
yaml_handler = YamlFileHandler()
playbook_handler = PlaybookHandler()

# Load and get the last row of spreadsheet data
spreadsheet_data = yaml_handler.aci_spreadsheet_data[-2:]

if __name__ == "__main__":
    playbook_handler.run_ansible_playbook(spreadsheet_data)

