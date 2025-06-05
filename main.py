
import subprocess
import os
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'

def run_ansible_playbook():
    vars_file = "./vars/aci_vars_01.yml"  # pass the vars file to the playbook

    result = subprocess.run(
        [
            "ansible-playbook",
            "-i", "inventory",
            "./cisco_aci/05_aci_deploy_app.yml",
            "--extra-vars", f"@{vars_file}"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)


if __name__ == "__main__":
    run_ansible_playbook()