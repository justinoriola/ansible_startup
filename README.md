# 🚀 ACI Ansible Automation

Automates Cisco ACI configuration generation and deployment using spreadsheet-driven input and Ansible.

---

## 📌 Overview

This project:
- Reads ACI configuration data from an Excel spreadsheet
- Transforms it into structured payloads
- Generates YAML configs
- Feeds into Ansible for deployment

---

## 📁 Project Structure

.
├── data/
│   └── aci_spreadsheet_data.xlsx   # REQUIRED input file
├── vars/
│   └── aci_config_*.yml            # Generated YAML files
├── file_handler.py
├── playbook_handler.py
└── README.md

---

## ⚙️ Requirements

- Python 3.10+

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 📄 Spreadsheet Requirements

Your input file **must**:

- Be named exactly:
```
aci_spreadsheet_data.xlsx
```

- Be located at:
```
./data/
```

If missing, you will see:

```
Spreadsheet not found: ensure 'aci_spreadsheet_data.xlsx' exists in ./data
```

---

## ▶️ Usage

Run in Python shell:

```python
from file_handler import FileHandler

file = FileHandler()
print(file._load_aci_spreadsheet_data(json_format=True))
```

---

## 🔍 Behavior

- Only rows where:
```
STATUS != "Done"
```
are processed.

- JSON output:
```python
file._load_aci_spreadsheet_data(json_format=True)
```

---

## 📤 Generate YAML Config

```python
for row in file.aci_spreadsheet_data:
    file.create_aci_yaml_files(row)
```

---

## ⚠️ Common Issues

| Issue | Fix |
|------|-----|
| Spreadsheet not found | Ensure file is in `./data/` |
| Empty output | Check `STATUS` column |
| Missing packages | `pip install pandas openpyxl` |

---

## 👤 Author

Justin – Network Automation Engineer
