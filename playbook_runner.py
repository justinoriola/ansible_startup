import os
import re
import json
import subprocess
import threading

class PlaybookRunner:
    def __init__(self):
        self.play_recap = ""
        self.task_name = None


    def run_playbook(self, file_name, epg_pair_in_progress, counter_label):
        """
        Run a single Ansible playbook with the given YAML variable file to deploy ACI EPGs.
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
            for line in process.stdout:

                if "TASK [" in line:
                    match = re.search(r'TASK \[(.*?)\]', line.strip())
                    if match:
                        self.task_name = match.group(1)
                        self.task_number = self.task_name.split('-')[0] if self.task_name else self.task_name
                        print(f"[#{counter_label}] Running ... {self.task_number}")

                elif "PLAY RECAP" in line:
                    self.play_recap += (f"\n[#{counter_label}] {line.strip().replace("*", '')}: "
                                        f"{epg_pair_in_progress}\n" + "-" * 110 + f"\n✅Deployment Succeeded: ")
                    success_flag = True

                elif success_flag and 'ok=' in line:
                    self.play_recap += line.removeprefix("sandboxapicdc.cisco.com    :")
                    print(self.play_recap)

                elif "failed=" in line and re.search(r'failed=\d+', line.strip()):
                    if re.search(r'failed=\d+[1-9]', line):  # failed count > 0
                        print(f"❌ [#{counter_label}] Deployment Failed: {self.task_number}: {line}")

                elif "msg" in line and "failed" in line.lower():
                    try:
                        match = re.search(r"=> (.*)$", line.strip())
                        if match:
                            error_msg = json.loads(match.group(1)).get("msg", "No error message found.")
                            print(f"❌ [#{counter_label}] Deployment Failed: {self.task_number} - {error_msg}")
                            break
                    except json.JSONDecodeError:
                        print(f"⚠️[#{counter_label}], Error parsing failure message.")

            process.wait()

        except Exception as e:
            print(f"💥 [#{counter_label}] Exception while running playbook for '{epg_pair_in_progress}': {e}")
