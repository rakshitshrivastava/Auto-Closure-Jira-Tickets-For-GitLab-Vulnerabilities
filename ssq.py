import requests
import re
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import sys


# Function to extract vulnerability IDs from the Jira issue description
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
        print("Description is not a recognized format.")
        return []

    # Match 9-digit IDs (vulnerability IDs)
    matches = re.findall(r'(\d{9})', text_content)
    unique_matches = list(set(matches))  # Remove duplicates
    return unique_matches

# Function to get the Jira issue details
def get_jira_issue(jira_url, issue_id, auth):
    """Fetch Jira issue details."""
    response = requests.get(f"{jira_url}/rest/api/2/issue/{issue_id}", auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch Jira issue: {response.status_code}")
        return None

# Function to upload a screenshot as an attachment to Jira
def upload_screenshot_to_jira(jira_url, issue_id, auth, screenshot_path, already_uploaded_ids):
    """Upload the screenshot to Jira as an attachment."""
    url = f"{jira_url}/rest/api/2/issue/{issue_id}/attachments"
    headers = {
        "X-Atlassian-Token": "no-check",  # Required to bypass CSRF check
    }
    
    # Ensure the file exists
    if not os.path.exists(screenshot_path):
        print(f"Screenshot file not found at {screenshot_path}")
        return None

    # Prevent uploading the same screenshot twice (based on screenshot_path or other criteria)
    if screenshot_path in already_uploaded_ids:
        print(f"Screenshot already uploaded for {screenshot_path}. Skipping upload.")
        return None

    files = {
        'file': open(screenshot_path, 'rb')
    }
    
    response = requests.post(url, auth=auth, headers=headers, files=files)
    
    if response.status_code == 200:
        # Parse the response to get the attachment ID or URL
        attachment_data = response.json()
        attachment_url = attachment_data[0]['content']
        print(f"Screenshot uploaded successfully. URL: {attachment_url}")
        
        # Track uploaded screenshot by its file path (or a unique ID)
        already_uploaded_ids.add(screenshot_path)
        return attachment_url
    else:
        print(f"Failed to upload screenshot: {response.status_code}, {response.text}")
        return None

# Function to add a comment with a screenshot link to Jira
def add_jira_comment(jira_url, issue_id, auth, comment_text, screenshot_url):
    """Add a comment with a screenshot link to the Jira issue."""
    url = f"{jira_url}/rest/api/2/issue/{issue_id}/comment"
    headers = {"Content-Type": "application/json"}

    # Prepare comment with screenshot link (if available)
    data = {
        "body": f"{comment_text} {screenshot_url}",
    }

    response = requests.post(url, auth=auth, json=data, headers=headers)

    if response.status_code == 201:
        print(f"Comment added to Jira issue: {issue_id}")
    else:
        print(f"Failed to add comment: {response.status_code}, {response.text}")

# Function to fetch vulnerability details from GitLab using GraphQL
def fetch_vulnerability_data(vulnerability_id, gitlab_url, gitlab_token):
    """Fetch vulnerability details using GitLab's GraphQL API."""
    time.sleep(2) 
    # GraphQL Query for vulnerability status
    query = """
    {
      vulnerability(id: "gid://gitlab/Vulnerability/{vulnerability_id}") {
        title
        description
        state
        severity
        reportType
        project {
          id
          name
          fullPath
        }
        detectedAt
        confirmedAt
        resolvedAt
        resolvedBy {
          id
          username
        }
      }
    }
    """.replace("{vulnerability_id}", vulnerability_id)

    headers = {
        "Authorization": f"Bearer {gitlab_token}",
        "Content-Type": "application/json",
    }

    # Make the GraphQL request
    response = requests.post(f"{gitlab_url}/api/graphql", json={"query": query}, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch vulnerability status: {response.status_code}, {response.text}")
        return None

# Function to take a screenshot of the API response
def take_screenshot_of_api_response(api_response, screenshot_name):
    """Take a screenshot of the JSON API response displayed in the browser."""
    
    # Prepare the response JSON string for displaying in the browser
    json_pretty = json.dumps(api_response, indent=4)
    
    # Setup Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")  # Disable GPU
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size

    # Use WebDriver Manager to avoid manual ChromeDriver installation
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Create a simple HTML page to render the API response
    html_content = f"""
    <html>
    <head>
        <title>API Response</title>
    </head>
    <body>
        <pre>{json_pretty}</pre>
    </body>
    </html>
    """
    
    # Save the content as an HTML file
    html_file = "api_response.html"
    with open(html_file, "w") as f:
        f.write(html_content)
    
    # Open the HTML file with the WebDriver
    driver.get(f"file://{os.path.abspath(html_file)}")
    
    # Wait for the page to load
    time.sleep(2)
    
    # Ensure the screenshots directory exists
    screenshot_dir = "screenshots"
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)
    
    # Define the screenshot path
    screenshot_path = os.path.join(screenshot_dir, f"{screenshot_name}.png")
    
    # Take a screenshot of the page displaying the API response
    driver.save_screenshot(screenshot_path)
    driver.quit()

    # Return the path of the screenshot
    return screenshot_path

# Main function
def main():
    # Configuration for Jira and GitLab
    jira_url = "https://yourdomain.atlassian.net"
    jira_username = "email"
    jira_api_key = "Jira_API"
    gitlab_url = "https://gitlab.com"  # Your GitLab URL
    gitlab_token = "gitlabapi"  # GitLab personal access token
    
    # Input Jira issue ID (modify as needed)
    ISSUE_KEY = sys.argv[1]
    issue_id =  ISSUE_KEY

    # Define Jira auth tuple
    auth = (jira_username, jira_api_key)

    # Get Jira issue data
    issue_data = get_jira_issue(jira_url, issue_id, auth)
    if not issue_data:
        return

    # Extract vulnerability IDs from the issue description
    vulnerability_ids = extract_vulnerability_ids(issue_data)
    print(f"Extracted vulnerability IDs: {vulnerability_ids}")  # Debugging line
    if not vulnerability_ids:
        return

    # Define a set to keep track of already uploaded screenshots
    already_uploaded_ids = set()

    # Process the first vulnerability ID (if you want to limit to one screenshot per Jira issue)
    vulnerability_id = vulnerability_ids[0]  # Select the first vulnerability ID only
    print(f"Processing only first vulnerability ID: {vulnerability_id}")

    # Fetch vulnerability details from GitLab
    api_response = fetch_vulnerability_data(vulnerability_id, gitlab_url, gitlab_token)
    if not api_response:
        print(f"No data found for vulnerability {vulnerability_id}")
        return
    
    # Take a screenshot of the API response
    screenshot_path = take_screenshot_of_api_response(api_response, f"vulnerability_{vulnerability_id}")
    if not screenshot_path:
        print(f"Failed to take screenshot for {vulnerability_id}")
        return

    # Upload the screenshot to Jira (track uploaded screenshots)
    screenshot_url = upload_screenshot_to_jira(jira_url, issue_id, auth, screenshot_path, already_uploaded_ids)
    if not screenshot_url:
        print(f"Failed to upload screenshot for {vulnerability_id}")
        return

    # Add a comment with the screenshot link to Jira
    comment_text = f"Evidence:-"
    add_jira_comment(jira_url, issue_id, auth, comment_text, screenshot_url)

if __name__ == "__main__":
    main()