import os
import re
import json
import subprocess
import threading
from threading import Lock
from file_handler import FileHandler
import queue

class PlaybookHandler:

    def __init__(self):
        self.play_recap = ""
        self.task_name = None
        self.results_queue = queue.Queue()
        self.failure_captured = False

    def run_ansible_playbook(self, epg_deployment_data):
        """
        Run Ansible playbooks concurrently using threads.
        Creates a new YamlFileHandler instance for each YAML file.
        """
        # Ensure aci_data is a list; if it's a dict, wrap it in a list
        if isinstance(epg_deployment_data, dict):
            epg_deployment_data = [epg_deployment_data]

        if not epg_deployment_data:
            print("🚫 No YAML variable data found for ACI deployment.")
            return

        threads = []
        counter_label = 1
        for data_row in epg_deployment_data:

            # Create a new handler for each file
            file_yaml_handler = FileHandler()

            # Create and persist YAML file for this data_row
            file_yaml_handler.create_aci_yaml_files(data_row)
            file_path = file_yaml_handler.yaml_file_path

            # Set the file name for the ACI YAML file
            epg_pair_in_progress = file_yaml_handler.safe_str(data_row.get("CONTRACT_NAME", "")).removeprefix('CON_')

            # Start a new thread to run the playbook
            thread = threading.Thread(
                target=self.run_playbook,
                args=(file_path, epg_pair_in_progress, counter_label)
            )
            thread.start()
            counter_label += 1
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        while not self.results_queue.empty():
            results.append(self.results_queue.get())
        return results

    def run_playbook(self, file_name, epg_pair_in_progress, counter_label):
        """
        Run a single Ansible playbook with the given YAML variable file to deploy ACI EPGs.
        The play recap will only be printed once the process completes.
        """
        try:
            print(f"== [#{counter_label}] Starting ACI EPG Deployment for: {epg_pair_in_progress} ==")

            process = subprocess.Popen(
                [
                    "ansible-playbook",
                    "-i", "inventory",
                    "cisco_aci/05_aci_deploy_app.yml",
                    "-e", f"@{file_name}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={**os.environ, "ANSIBLE_FORCE_COLOR": "false"}
            )

            success_flag = False
            recap_buffer = ""


            for line in process.stdout:
                line = line.strip()

                # Error capture
                if "msg" in line and "fatal:" in line.lower():

                    try:
                        match = re.search(r'=> (.*)$', line)
                        if match:
                            error_msg = json.loads(match.group(1)).get("msg", "No error message found.")
                            recap_buffer += (
                                    f"\n[#{counter_label}] PLAY RECAP: {epg_pair_in_progress}\n"
                                    + '-' * 157 +
                                    f"\n❌ Deployment Failed @[{self.task_number}] - {error_msg}\n"
                            )

                            self.failure_captured = True
                            break   # Exit loop on error

                    except json.JSONDecodeError:
                        recap_buffer += f"\n⚠️ [#{counter_label}] Error parsing failure message.\n"
                        self.failure_captured = True
                        break

                # Task tracking
                elif "TASK [" in line:
                    match = re.search(r'TASK \[(.*?)\]', line)
                    if match:
                        self.task_name = match.group(1)
                        self.task_number = self.task_name.split('-')[0] if self.task_name else "?"
                        print(f"[#{counter_label}] Running ... {self.task_name}")

                # Play recap capture
                elif "PLAY RECAP" in line:
                    success_flag = True
                    with Lock():
                        recap_buffer += (
                                f"\n[#{counter_label}] PLAY RECAP : {epg_pair_in_progress}\n" + '-' * 110 +
                                "\n✅ Deployment Succeeded"
                        )
                # Add recap content
                elif success_flag and "sandboxapicdc.cisco.com" in line:
                    recap_buffer += line.replace("sandboxapicdc.cisco.com", "").strip() + "\n\n"

            process.wait()
            # Print only once after the loop
            if recap_buffer:
                print(recap_buffer.strip())
            self.results_queue.put(process.returncode)
        except Exception as e:
            print(f"💥 [#{counter_label}] Exception while running playbook for '{epg_pair_in_progress}': {e}")