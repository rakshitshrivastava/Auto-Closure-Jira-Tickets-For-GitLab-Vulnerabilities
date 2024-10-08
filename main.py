import requests
import re
import json
import logging
import urllib3
import pandas as pd
import subprocess
import time
from tqdm import tqdm
import ssq

# Initialize logging
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s"
    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
urllib3.disable_warnings()
ch = TqdmLoggingHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

# JIRA API configuration
JIRA_API_TOKEN = "JIRA_API"
JIRA_EMAIL = "email"
JIRA_BASE_URL = 'https://yourdomain.atlassian.net'

# GitLab API configuration
gitlab_api_token = 'gitlab_api'
gitlab_base_url = 'https://gitlab.com/api/v4'
gitlab_headers = {
    'Private-Token': gitlab_api_token
}

def fetch_jira_issue(issue_id):
    """Fetches a Jira issue and returns its data."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_id}"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    response = requests.get(url, auth=auth)

    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error fetching issue: {response.status_code} - {response.text}")
        return None

def extract_vulnerability_ids(issue_data):
    """Extracts unique vulnerability IDs from the Jira issue description."""
    description = issue_data.get('fields', {}).get('description', '')

    if isinstance(description, str):
        text_content = description
    elif isinstance(description, dict):
        text_content = ""
        for content in description.get('content', []):
            if content.get('type') == 'paragraph':
                for text in content.get('content', []):
                    if 'text' in text:
                        text_content += text['text']
    else:
        logger.error("Description is not a recognized format.")
        return []

    matches = re.findall(r'(\d{9})', text_content)  # Matches 9-digit IDs
    unique_matches = list(set(matches))  # Remove duplicates
    return unique_matches

def make_request(url, headers):
    """Makes a GET request to the given URL with headers."""
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

def check_vulnerability_resolved(vulnerability_id):
    """Checks if a vulnerability is resolved."""
    url = f"{gitlab_base_url}/vulnerabilities/{vulnerability_id}"
    response = make_request(url, gitlab_headers)
    if response:
        data = response.json()
        resolved_on_default_branch = data.get("resolved_on_default_branch", 0)
        return int(resolved_on_default_branch) == 1
    return False

def change_issue_status(issue_key, new_status):
    """Changes the status of a Jira issue."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/transitions"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    # Define the payload with the new status ID
    payload = {
        "transition": {
            "id": new_status  # Must be an integer
        }
    }

    response = requests.post(url, json=payload, auth=auth)

    if response.status_code == 204:
        logger.info(f"Issue {issue_key} status changed to {new_status}.")
        return True
    else:
        logger.error(f"Error changing issue status: {response.status_code} - {response.text}")
        return False

def perform_action(action, vuln_id):
    """Perform actions (resolve, revert, dismiss) on a vulnerability."""
    url = f"{gitlab_base_url}/vulnerabilities/{vuln_id}/{action}"
    headers = {
        "Private-Token": gitlab_api_token
    }
    response = requests.post(url, headers=headers)

    if response.status_code in (200, 201):
        return f"Successfully {action} vulnerability with ID {vuln_id}."
    elif response.status_code == 304:
        return f"Skipped vulnerability ID {vuln_id} (already {action})."
    else:
        return f"Failed to {action} vulnerability ID {vuln_id} (Status code: {response.status_code})"

def read_ticket_keys_from_excel(file_path):
    df = pd.read_excel(file_path)
    return df['Id'].dropna().astype(str).tolist()

def write_ticket_keys_to_excel(issue_keys, output_file):
    df = pd.DataFrame(issue_keys, columns=['JIRA_TICKET'])
    df.to_excel(output_file, index=False)

def fetch_issues(jql):
    url = f'{JIRA_BASE_URL}/rest/api/2/search'
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {'Content-Type': 'application/json'}

    issues = []
    start_at = 0
    max_results = 100

    print("Fetching issues...")
    while True:
        params = {
            'jql': jql,
            'fields': 'summary,status,assignee,reporter',
            'startAt': start_at,
            'maxResults': max_results
        }

        response = requests.get(url, headers=headers, auth=auth, params=params)

        if response.status_code != 200:
            raise Exception(f"Error fetching issues: {response.status_code} - {response.text}")

        data = response.json()
        issues.extend(data.get('issues', []))

        print(f"Fetched {len(data.get('issues', []))} issues starting at {start_at}.")

        if start_at + max_results >= data['total']:
            break

        start_at += max_results

    print(f"Total issues fetched: {len(issues)}")
    return issues

# Add comment to Jira issue
def add_jira_comment(issue_key, comment_text):
    """Adds a comment to a Jira issue."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/comment"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "body": comment_text
    }

    response = requests.post(url, json=payload, auth=auth, headers=headers)

    if response.status_code == 201:
        logger.info(f"Added comment to issue {issue_key}: {comment_text}")
    else:
        logger.error(f"Failed to add comment to issue {issue_key}: {response.status_code} - {response.text}")

def add_jira_label(issue_key, labels):
    """Adds labels to a Jira issue."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Content-Type": "application/json"
    }

    # Prepare the payload for updating labels
    payload = {
        "update": {
            "labels": [{"add": label} for label in labels]
        }
    }

    # Make the PUT request to Jira to update the labels
    response = requests.put(url, auth=auth, headers=headers, data=json.dumps(payload))

    # Check if the request was successful
    if response.status_code == 204:
        print(f"Labels {labels} successfully added to issue {issue_key}.")
    else:
        print(f"Failed to add labels. Status code: {response.status_code}, Response: {response.text}")

def main():
    # Choose between Excel or JQL input
    choice = input("What's the menu on my food platter? (type 'excel' or 'jql'): ").strip().lower()

    if choice == 'excel':
        excel_file = 'reval.xlsx'
        issue_keys = read_ticket_keys_from_excel(excel_file)
    elif choice == 'jql':
        print('Enter your JQL query (type "END" on a new line to finish):')

        jql_lines = []
        while True:
            line = input()
            if line.strip().upper() == 'END':
                break
            jql_lines.append(line)

        jql_query = ' '.join(jql_lines)
        print(f"You entered: {jql_query}. Is this correct? (yes/no)")
        confirmation = input().strip().lower()

        if confirmation == 'yes':
            issues = fetch_issues(jql_query)
            issue_keys = [issue['key'] for issue in issues]
            output_file = 'output.xlsx'
            write_ticket_keys_to_excel(issue_keys, output_file)
            print(f"Wrote {len(issue_keys)} issues to {output_file}.")
        else:
            print("Please try again.")
            exit(1)
    else:
        print("Invalid choice. Please type 'excel' or 'jql'.")
        exit(1)

    for ISSUE_KEY in issue_keys:
        logger.info(f"Processing Jira Issue: {ISSUE_KEY}")
        issue_data = fetch_jira_issue(ISSUE_KEY)  # Implement this function
        if issue_data:
            vulnerability_ids = extract_vulnerability_ids(issue_data)  # Implement this function
            logger.info(f"Fetched unique vulnerability IDs: {vulnerability_ids}")

            # Check which vulnerabilities are resolved
            resolved_vulns = [vuln_id for vuln_id in vulnerability_ids if check_vulnerability_resolved(vuln_id)]  # Implement this function
            logger.info(f"Vulnerabilities resolved in development: {resolved_vulns}")

            # Change the issue status if vulnerabilities are resolved
            if resolved_vulns:
                resolved_status_id = ""  # Replace with your actual transition ID
                if change_issue_status(ISSUE_KEY, resolved_status_id):  # Implement this function
                    logger.info(f"Issue {ISSUE_KEY} status changed to resolved due to vulnerabilities: {resolved_vulns}")

                    # Perform actions on each resolved vulnerability
                    for vuln_id in resolved_vulns:
                        action_result = perform_action("resolve", vuln_id)  # Implement this function
                        logger.info(action_result)

                    # Add comment on Jira issue
                    time.sleep(1.100)
                    add_jira_comment(ISSUE_KEY, "The issue has been resolved. Please check the attachment .")
                    # Adding Label
                    add_jira_label(ISSUE_KEY, labels=["Automation_Closed", "Issue_Resolved"])
                    time.sleep(1.100)
                    time.sleep(5) 
                    logger.info("Running SSD script...")
                    subprocess.run(['python3', 'ssq.py', ISSUE_KEY ], check=True )  # Adjust the path if needed
                    
                else:
                    logger.error(f"Failed to change status of issue {ISSUE_KEY}.")
            else:
                logger.info(f"No vulnerabilities resolved in development for issue {ISSUE_KEY}.")
                # Add comment on Jira issue
                add_jira_comment(ISSUE_KEY, "The issue is not fixed based on the automated validation results. Please refer to the evidence in the comment below for further details.")
                add_jira_label(ISSUE_KEY, labels=["Issue_Open" ])
                time.sleep(5) 
                logger.info("Running SSD script...")
                subprocess.run(['python3', 'ssq.py', ISSUE_KEY ], check=True )  # Adjust the path if needed
                
    

if __name__ == "__main__":
    main()
