# Auto-Closure-Jira-Tickets-For-GitLab-Vulnerabilities

This repository contains an automation tool that integrates Jira and GitLab APIs to streamline the management of Jira tickets associated with GitLab vulnerabilities. It automatically closes Jira issues when the corresponding vulnerabilities are resolved in GitLab, enhancing workflow efficiency and reducing manual oversight.

## Prerequisites

1. **Python Version**: Ensure Python 3.6+ is installed.
2. **Required Python Libraries**: Install the necessary libraries by running:
   ```bash
   pip install -r requirements.txt
                   or
   pip3 install requests pandas tqdm selenium webdriver-manager urllib3

**External Dependencies**
Jira API: Jira account credentials and API token are required to interact with Jira.
GitLab API: GitLab personal access token is required for fetching vulnerability data.
Excel File: To read ticket keys from Excel files and process them.

**Setup Authentication**
Before running the scripts, make sure to update the following credentials in the script:

JIRA_API_TOKEN: Your Jira API token.
JIRA_EMAIL: Your Jira email.
JIRA_BASE_URL: Your Jira instance URL.
gitlab_api_token: Your GitLab personal access token.
gitlab_base_url: GitLab API base URL.
resolved_status_id = ""  # Replace with your actual transition ID


**Scripts Description**
1. Main Script (main.py)
This script is responsible for fetching Jira issues either from an Excel file or by using a JQL query, extracting vulnerability IDs, checking their status in GitLab, and updating the Jira issue accordingly.

**Key functions include:**

fetch_jira_issue(issue_id): Fetches Jira issue details.

extract_vulnerability_ids(issue_data): Extracts vulnerability IDs from Jira issue descriptions.

check_vulnerability_resolved(vulnerability_id): Checks if a vulnerability is resolved in GitLab.

change_issue_status(issue_key, new_status): Changes the status of a Jira issue.

add_jira_comment(issue_key, comment_text): Adds a comment to a Jira issue.

add_jira_label(issue_key, labels): Adds labels to a Jira issue.

perform_action(action, vuln_id): Resolves vulnerabilities in GitLab and performs other actions.

read_ticket_keys_from_excel(file_path): Reads ticket keys from an Excel file.

write_ticket_keys_to_excel(issue_keys, output_file): Writes the issue keys to an Excel file.

**Screenshot Script (ssq.py):-** 
This script interacts with Jira and GitLab to fetch vulnerability data, take screenshots of the API response, and attach them to Jira tickets.

**Key functions include:**

extract_vulnerability_ids(issue_data): Extracts vulnerability IDs from Jira issues.

upload_screenshot_to_jira(jira_url, issue_id, auth, screenshot_path, already_uploaded_ids): Uploads a screenshot to Jira.

add_jira_comment(jira_url, issue_id, auth, comment_text, screenshot_url): Adds a Jira comment with a screenshot link.

fetch_vulnerability_data(vulnerability_id, gitlab_url, gitlab_token): Fetches vulnerability details from GitLab.

take_screenshot_of_api_response(api_response, screenshot_name): Takes a screenshot of the API response and saves it.

How to run the script and It's output 

![image](https://github.com/user-attachments/assets/c3b556de-9048-4dd3-b4ee-ce6ec0e3c847)





![image](https://github.com/user-attachments/assets/03c435fa-4321-43d8-af90-50a17d813159)


