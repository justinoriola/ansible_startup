
import subprocess
import os
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'

def run_ansible_playbook():
    result = subprocess.run(
        ["ansible-playbook", "-i", "./ansible_startup/hosts.yml", "./ansible_startup/cisco.yml"],
        capture_output=True,
        text=True
    )
    # print(result)
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)


if __name__ == "__main__":
    run_ansible_playbook()