#!/usr/bin/env python3
"""
Jira-Aha Synchronization Script
This script synchronizes Jira issues with Aha ideas by:
1. Fetching Jira issues from a specified project
2. Getting Aha idea details using reference numbers
3. Updating Jira issues with Aha descriptions and attachments
"""

import requests
import json
import base64
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration class for API credentials and settings"""
    # Jira Configuration
    jira_url: str
    jira_username: str
    jira_token: str
    jira_project_key: str
    jira_aha_reference_field: str = "customfield_12345"  # Update with actual field ID
    
    # Aha Configuration
    aha_domain: str  # e.g., "yourcompany.aha.io"
    aha_api_key: str
    
    # Sync Configuration
    update_description: bool = True
    update_attachments: bool = True
    dry_run: bool = False
    test_run: bool = False
    test_issue_limit: int = 3
    
    # Additional fields to sync (customize as needed)
    additional_field_mappings: Dict[str, str] = None
    
    def __post_init__(self):
        if self.additional_field_mappings is None:
            self.additional_field_mappings = {
                # Example mappings - customize these based on your needs
                # "aha_field_name": "jira_field_id"
                # "status": "customfield_10001",
                # "priority": "customfield_10002"
            }

class JiraAhaSync:
    def __init__(self, config: Config):
        self.config = config
        self.jira_auth = (config.jira_username, config.jira_token)
        self.aha_headers = {
            'Authorization': f'Bearer {config.aha_api_key}',
            'Content-Type': 'application/json'
        }
        
    def get_jira_issues(self) -> List[Dict[str, Any]]:
        """Fetch Jira issues from the specified project that have Aha reference numbers"""
        jql = f'project = "{self.config.jira_project_key}" AND "{self.config.jira_aha_reference_field}" is not EMPTY'
        
        url = urljoin(self.config.jira_url, '/rest/api/3/search')
        params = {
            'jql': jql,
            'fields': f'key,summary,description,attachment,{self.config.jira_aha_reference_field}',
            'maxResults': self.config.test_issue_limit if self.config.test_run else 100
        }
        
        try:
            response = requests.get(url, params=params, auth=self.jira_auth)
            response.raise_for_status()
            
            data = response.json()
            issues = data.get('issues', [])
            
            if self.config.test_run:
                logger.info(f"TEST RUN: Limiting to {len(issues)} issues (max {self.config.test_issue_limit})")
            
            logger.info(f"Found {len(issues)} Jira issues with Aha references")
            return issues
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Jira issues: {e}")
            return []
    
    def get_aha_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Fetch idea details from Aha"""
        url = f"https://{self.config.aha_domain}/api/v1/ideas/{idea_id}"
        
        try:
            response = requests.get(url, headers=self.aha_headers)
            response.raise_for_status()
            
            idea_data = response.json()
            logger.info(f"Successfully fetched Aha idea: {idea_id}")
            return idea_data.get('idea', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Aha idea {idea_id}: {e}")
            return None
    
    def get_aha_attachments(self, idea_id: str) -> List[Dict[str, Any]]:
        """Fetch attachments for an Aha idea"""
        url = f"https://{self.config.aha_domain}/api/v1/ideas/{idea_id}/attachments"
        
        try:
            response = requests.get(url, headers=self.aha_headers)
            response.raise_for_status()
            
            data = response.json()
            attachments = data.get('attachments', [])
            logger.info(f"Found {len(attachments)} attachments for idea {idea_id}")
            return attachments
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching attachments for idea {idea_id}: {e}")
            return []
    
    def download_attachment(self, attachment_url: str) -> Optional[bytes]:
        """Download attachment content from Aha"""
        try:
            response = requests.get(attachment_url, headers=self.aha_headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading attachment {attachment_url}: {e}")
            return None
    
    def upload_attachment_to_jira(self, issue_key: str, filename: str, content: bytes) -> bool:
        """Upload attachment to Jira issue"""
        url = urljoin(self.config.jira_url, f'/rest/api/3/issue/{issue_key}/attachments')
        
        files = {'file': (filename, content)}
        headers = {'X-Atlassian-Token': 'no-check'}
        
        try:
            response = requests.post(url, files=files, headers=headers, auth=self.jira_auth)
            response.raise_for_status()
            logger.info(f"Successfully uploaded attachment {filename} to {issue_key}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading attachment {filename} to {issue_key}: {e}")
            return False
    
    def update_jira_issue(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """Update Jira issue with provided fields"""
        url = urljoin(self.config.jira_url, f'/rest/api/3/issue/{issue_key}')
        
        update_data = {
            'fields': fields
        }
        
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would update {issue_key} with fields: {list(fields.keys())}")
            return True
        
        try:
            response = requests.put(url, json=update_data, auth=self.jira_auth)
            response.raise_for_status()
            logger.info(f"Successfully updated Jira issue {issue_key}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Jira issue {issue_key}: {e}")
            return False
    
    def sync_issue_with_aha(self, jira_issue: Dict[str, Any]) -> bool:
        """Sync a single Jira issue with its corresponding Aha idea"""
        issue_key = jira_issue['key']
        fields = jira_issue['fields']
        
        # Get Aha reference number
        aha_reference = fields.get(self.config.jira_aha_reference_field)
        if not aha_reference:
            logger.warning(f"No Aha reference found for issue {issue_key}")
            return False
        
        logger.info(f"Syncing {issue_key} with Aha idea {aha_reference}")
        
        # Fetch Aha idea
        aha_idea = self.get_aha_idea(aha_reference)
        if not aha_idea:
            return False
        
        # Prepare update fields
        update_fields = {}
        
        # Update description if enabled
        if self.config.update_description and aha_idea.get('description'):
            # Convert Aha description format if needed (Aha uses HTML, Jira might use different format)
            aha_description = aha_idea['description']
            update_fields['description'] = {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'text',
                                'text': f"Synced from Aha:\n{aha_description}"
                            }
                        ]
                    }
                ]
            }
        
        # Sync additional fields
        for aha_field, jira_field in self.config.additional_field_mappings.items():
            if aha_field in aha_idea:
                update_fields[jira_field] = aha_idea[aha_field]
        
        # Update Jira issue with description and additional fields
        success = True
        if update_fields:
            success = self.update_jira_issue(issue_key, update_fields)
        
        # Handle attachments if enabled
        if self.config.update_attachments and success:
            attachments = self.get_aha_attachments(aha_reference)
            for attachment in attachments:
                attachment_url = attachment.get('download_url')
                filename = attachment.get('filename', f"aha_attachment_{attachment.get('id')}")
                
                if attachment_url:
                    content = self.download_attachment(attachment_url)
                    if content:
                        self.upload_attachment_to_jira(issue_key, filename, content)
        
        return success
    
    def run_sync(self) -> None:
        """Main synchronization process"""
        logger.info("Starting Jira-Aha synchronization")
        
        if self.config.test_run:
            logger.info(f"Running in TEST mode - processing max {self.config.test_issue_limit} issues")
        
        if self.config.dry_run:
            logger.info("Running in DRY RUN mode - no changes will be made")
        
        # Get all Jira issues with Aha references
        jira_issues = self.get_jira_issues()
        
        if not jira_issues:
            logger.warning("No Jira issues found with Aha references")
            return
        
        # Process each issue
        success_count = 0
        for issue in jira_issues:
            try:
                if self.sync_issue_with_aha(issue):
                    success_count += 1
            except Exception as e:
                logger.error(f"Unexpected error processing issue {issue['key']}: {e}")
        
        logger.info(f"Synchronization complete. Successfully processed {success_count}/{len(jira_issues)} issues")

def load_config_from_env() -> Config:
    """Load configuration from environment variables"""
    return Config(
        jira_url=os.getenv('JIRA_URL', 'https://your-domain.atlassian.net'),
        jira_username=os.getenv('JIRA_USERNAME', ''),
        jira_token=os.getenv('JIRA_TOKEN', ''),
        jira_project_key=os.getenv('JIRA_PROJECT_KEY', ''),
        jira_aha_reference_field=os.getenv('JIRA_AHA_FIELD', 'customfield_12345'),
        aha_domain=os.getenv('AHA_DOMAIN', 'yourcompany.aha.io'),
        aha_api_key=os.getenv('AHA_API_KEY', ''),
        update_description=os.getenv('UPDATE_DESCRIPTION', 'true').lower() == 'true',
        update_attachments=os.getenv('UPDATE_ATTACHMENTS', 'true').lower() == 'true',
        dry_run=os.getenv('DRY_RUN', 'false').lower() == 'true',
        test_run=os.getenv('TEST_RUN', 'false').lower() == 'true',
        test_issue_limit=int(os.getenv('TEST_ISSUE_LIMIT', '3'))
    )

def main():
    """Main function"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Jira-Aha Synchronization Script')
    parser.add_argument('--test', action='store_true', 
                       help='Run in test mode (process limited number of issues)')
    parser.add_argument('--test-limit', type=int, default=3, choices=range(1, 6),
                       help='Number of issues to process in test mode (1-5, default: 3)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without making any changes')
    parser.add_argument('--list-issues', action='store_true',
                       help='List issues that would be processed and exit')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config_from_env()
    
    # Override config with command line arguments
    if args.test:
        config.test_run = True
        config.test_issue_limit = args.test_limit
        logger.info(f"Test mode enabled - will process max {config.test_issue_limit} issues")
    
    if args.dry_run:
        config.dry_run = True
        logger.info("Dry run mode enabled - no changes will be made")
    
    # Validate required configuration
    required_fields = [
        'jira_url', 'jira_username', 'jira_token', 'jira_project_key',
        'aha_domain', 'aha_api_key'
    ]
    
    missing_fields = [field for field in required_fields if not getattr(config, field)]
    
    if missing_fields:
        logger.error(f"Missing required configuration: {', '.join(missing_fields)}")
        logger.error("Please set the following environment variables:")
        for field in missing_fields:
            logger.error(f"  {field.upper()}")
        return
    
    # Create sync instance
    sync = JiraAhaSync(config)
    
    # Handle list-issues command
    if args.list_issues:
        logger.info("Listing issues that would be processed:")
        issues = sync.get_jira_issues()
        if issues:
            logger.info(f"Found {len(issues)} issues with Aha references:")
            for i, issue in enumerate(issues, 1):
                fields = issue['fields']
                aha_ref = fields.get(config.jira_aha_reference_field, 'N/A')
                logger.info(f"  {i}. {issue['key']}: {fields.get('summary', 'No summary')} (Aha: {aha_ref})")
        else:
            logger.info("No issues found with Aha references")
        return
    
    # Run sync
    sync.run_sync()

if __name__ == "__main__":
    main()
