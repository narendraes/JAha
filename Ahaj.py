#!/usr/bin/env python3
"""
Aha! to Jira Integration Script
Fetches ideas from Aha! workspace and creates corresponding Jira issues
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import os
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aha_jira_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AhaJiraSync:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the sync tool with configuration"""
        self.config = config
        self.aha_headers = {
            'Authorization': f'Bearer {config["aha"]["api_token"]}',
            'Content-Type': 'application/json'
        }
        self.jira_auth = (config['jira']['username'], config['jira']['api_token'])
        self.jira_headers = {
            'Content-Type': 'application/json'
        }
        
        # Rate limiting
        self.last_aha_request = 0
        self.last_jira_request = 0
        self.aha_rate_limit = 1.0  # seconds between requests
        self.jira_rate_limit = 0.5  # seconds between requests
        
    def _rate_limit_aha(self):
        """Implement rate limiting for Aha! API"""
        elapsed = time.time() - self.last_aha_request
        if elapsed < self.aha_rate_limit:
            time.sleep(self.aha_rate_limit - elapsed)
        self.last_aha_request = time.time()
    
    def _rate_limit_jira(self):
        """Implement rate limiting for Jira API"""
        elapsed = time.time() - self.last_jira_request
        if elapsed < self.jira_rate_limit:
            time.sleep(self.jira_rate_limit - elapsed)
        self.last_jira_request = time.time()
    
    def fetch_ideas_list(self, product_id: str) -> List[Dict]:
        """Fetch list of ideas from Aha! for a specific product"""
        self._rate_limit_aha()
        
        url = f"{self.config['aha']['base_url']}/api/v1/products/{product_id}/ideas"
        params = {
            'per_page': 100,  # Adjust as needed
            'page': 1
        }
        
        all_ideas = []
        
        try:
            while True:
                logger.info(f"Fetching ideas page {params['page']}")
                response = requests.get(url, headers=self.aha_headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                ideas = data.get('ideas', [])
                
                if not ideas:
                    break
                    
                all_ideas.extend(ideas)
                
                # Check if there are more pages
                if len(ideas) < params['per_page']:
                    break
                    
                params['page'] += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ideas list: {e}")
            raise
            
        logger.info(f"Fetched {len(all_ideas)} ideas from Aha!")
        return all_ideas
    
    def fetch_idea_comments(self, idea_id: str) -> List[Dict]:
        """Fetch comments for a specific idea"""
        self._rate_limit_aha()
        
        url = f"{self.config['aha']['base_url']}/api/v1/ideas/{idea_id}/comments"
        
        try:
            response = requests.get(url, headers=self.aha_headers)
            response.raise_for_status()
            return response.json().get('comments', [])
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching comments for idea {idea_id}: {e}")
            return []
    
    def format_comments_for_jira(self, comments: List[Dict]) -> str:
        """Format Aha! comments into a single Jira comment"""
        if not comments:
            return ""
        
        formatted_comments = ["*Comments from Aha!:*", ""]
        
        for comment in comments:
            created_by = comment.get('created_by', {})
            author_name = created_by.get('name', 'Unknown User')
            author_email = created_by.get('email', '')
            created_at = comment.get('created_at', 'Unknown Date')
            body = comment.get('body', 'No content')
            
            comment_header = f"*Commented by:* {author_name}"
            if author_email:
                comment_header += f" ({author_email})"
            comment_header += f" on {created_at}"
            
            formatted_comments.extend([
                "---",
                comment_header,
                body,
                ""
            ])
        
        return "\n".join(formatted_comments)
        """Fetch detailed information for a specific idea"""
        self._rate_limit_aha()
        
        url = f"{self.config['aha']['base_url']}/api/v1/ideas/{idea_id}"
        
        try:
            response = requests.get(url, headers=self.aha_headers)
            response.raise_for_status()
            return response.json()['idea']
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching idea {idea_id}: {e}")
            raise
    
    def format_description(self, idea: Dict) -> str:
        """Format the Jira description with idea details and custom fields"""
        description_parts = []
        
        # Add original description if available
        if idea.get('description'):
            description_parts.append("*Original Description:*")
            description_parts.append(idea['description'])
            description_parts.append("")
        
        # Add Aha! URL
        if idea.get('url'):
            description_parts.append(f"*Aha! Link:* {idea['url']}")
            description_parts.append("")
        
        # Add idea score if available
        if idea.get('score'):
            description_parts.append(f"*Score:* {idea['score']}")
        
        # Add categories
        if idea.get('categories'):
            categories = [cat.get('name', '') for cat in idea['categories']]
            description_parts.append(f"*Categories:* {', '.join(categories)}")
        
        # Add custom fields (configurable ones only)
        selected_custom_fields = self.config.get('field_mappings', {}).get('description_custom_fields', [])
        if idea.get('custom_fields') and selected_custom_fields:
            description_parts.append("")
            description_parts.append("*Custom Fields:*")
            for field in idea['custom_fields']:
                field_name = field.get('name', 'Unknown Field')
                if field_name in selected_custom_fields:
                    field_value = field.get('value', 'N/A')
                    description_parts.append(f"• *{field_name}:* {field_value}")
        
        # Add portal information
        if idea.get('portal'):
            portal_info = idea['portal']
            description_parts.append("")
            description_parts.append("*Portal Information:*")
            description_parts.append(f"• *Portal:* {portal_info.get('name', 'N/A')}")
            if portal_info.get('url'):
                description_parts.append(f"• *Portal URL:* {portal_info['url']}")
        
        # Add created by information
        if idea.get('created_by'):
            created_by = idea['created_by']
            description_parts.append("")
            description_parts.append(f"*Created by:* {created_by.get('name', 'Unknown')} ({created_by.get('email', 'N/A')})")
        
        # Add timestamps
        if idea.get('created_at'):
            description_parts.append(f"*Created:* {idea['created_at']}")
        
        # Add feature information if available
        if idea.get('feature'):
            feature = idea['feature']
            description_parts.append("")
            description_parts.append("*Related Feature:*")
            if feature.get('reference_num'):
                description_parts.append(f"• *Feature Reference:* {feature['reference_num']}")
            if feature.get('url'):
                description_parts.append(f"• *Feature URL:* {feature['url']}")
            if feature.get('name'):
                description_parts.append(f"• *Feature Name:* {feature['name']}")
        
        return "\n".join(description_parts)
    
    def map_assignee(self, idea: Dict) -> Optional[str]:
        """Map Aha! assignee to Jira user"""
        if not idea.get('assigned_to'):
            return None
            
        assigned_to = idea['assigned_to']
        aha_email = assigned_to.get('email')
        
        if not aha_email:
            return None
        
        # Check if there's a mapping in config
        email_mappings = self.config.get('field_mappings', {}).get('assignee_mappings', {})
        if aha_email in email_mappings:
            return email_mappings[aha_email]
        
        # Try to find Jira user by email
        return self.find_jira_user_by_email(aha_email)
    
    def find_jira_user_by_email(self, email: str) -> Optional[str]:
        """Find Jira user account ID by email"""
        self._rate_limit_jira()
        
        try:
            url = f"{self.config['jira']['base_url']}/rest/api/3/user/search"
            params = {'query': email}
            
            response = requests.get(url, headers=self.jira_headers, auth=self.jira_auth, params=params)
            response.raise_for_status()
            
            users = response.json()
            if users:
                return users[0]['accountId']
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not find Jira user for email {email}: {e}")
        
        return None
    
    def map_status(self, idea: Dict) -> str:
        """Map Aha! workflow status to Jira status"""
        aha_status = idea.get('workflow_status', {}).get('name', 'New')
        
        # Get status mappings from config
        status_mappings = self.config.get('field_mappings', {}).get('status_mappings', {})
        
        return status_mappings.get(aha_status, self.config['jira']['default_status'])
    
    def add_comment_to_jira_issue(self, issue_key: str, comment_text: str) -> bool:
        """Add a comment to a Jira issue"""
        if not comment_text.strip():
            return True
            
        self._rate_limit_jira()
        
        comment_data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment_text
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            url = f"{self.config['jira']['base_url']}/rest/api/3/issue/{issue_key}/comment"
            response = requests.post(url, headers=self.jira_headers, auth=self.jira_auth,
                                   data=json.dumps(comment_data))
            response.raise_for_status()
            logger.info(f"Added comments to Jira issue {issue_key}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding comment to Jira issue {issue_key}: {e}")
            return False
    
    def add_web_link_to_jira_issue(self, issue_key: str, url: str, title: str = "Aha! Idea") -> bool:
        """Add a web link to a Jira issue"""
        if not url:
            return True
            
        self._rate_limit_jira()
        
        link_data = {
            "object": {
                "url": url,
                "title": title
            }
        }
        
        try:
            api_url = f"{self.config['jira']['base_url']}/rest/api/3/issue/{issue_key}/remotelink"
            response = requests.post(api_url, headers=self.jira_headers, auth=self.jira_auth,
                                   data=json.dumps(link_data))
            response.raise_for_status()
            logger.info(f"Added web link to Jira issue {issue_key}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding web link to Jira issue {issue_key}: {e}")
            return False
        """Map idea score or other fields to Jira priority"""
        # Use score to determine priority
        score = idea.get('score', 0)
        
        priority_mappings = self.config.get('field_mappings', {}).get('priority_mappings', {
            'high': 'High',
            'medium': 'Medium', 
            'low': 'Low'
        })
        
        if score >= 80:
            return priority_mappings.get('high', 'High')
        elif score >= 50:
            return priority_mappings.get('medium', 'Medium')
        else:
            return priority_mappings.get('low', 'Low')
    
    def create_jira_issue(self, idea: Dict) -> Optional[str]:
        """Create a Jira issue from an Aha! idea"""
        self._rate_limit_jira()
        
        # Build the issue payload
        issue_data = {
            "fields": {
                "project": {"key": self.config['jira']['project_key']},
                "summary": idea.get('name', 'Untitled Idea'),
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.format_description(idea)
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": self.config['jira']['issue_type']},
                "priority": {"name": self.map_priority(idea)}
            }
        }
        
        # Add assignee if available
        assignee = self.map_assignee(idea)
        if assignee:
            issue_data["fields"]["assignee"] = {"accountId": assignee}
        
        # Add labels
        labels = []
        if idea.get('categories'):
            labels.extend([cat.get('name', '').replace(' ', '_') for cat in idea['categories']])
        labels.append('aha-import')
        issue_data["fields"]["labels"] = labels
        
        # Add standard field mappings
        field_mappings = self.config.get('field_mappings', {})
        
        # Map reference_num to Xref-ID
        if idea.get('reference_num') and field_mappings.get('xref_id_field'):
            issue_data["fields"][field_mappings['xref_id_field']] = idea['reference_num']
        
        # Map created_at to Xref-Created
        if idea.get('created_at') and field_mappings.get('xref_created_field'):
            # Convert datetime format if needed
            created_date = idea['created_at']
            if 'T' in created_date:
                created_date = created_date.split('T')[0]  # Get just the date part
            issue_data["fields"][field_mappings['xref_created_field']] = created_date
        
        # Map created_by email to Xref-Reporter
        if idea.get('created_by', {}).get('email') and field_mappings.get('xref_reporter_field'):
            issue_data["fields"][field_mappings['xref_reporter_field']] = idea['created_by']['email']
        
        # Add custom fields if configured
        custom_fields = field_mappings.get('custom_fields', {})
        for aha_field_path, jira_field in custom_fields.items():
            # Support nested field access (e.g., "custom_fields.field_name")
            field_value = self.get_nested_field_value(idea, aha_field_path)
            if field_value is not None:
                issue_data["fields"][jira_field] = field_value
        
        try:
            url = f"{self.config['jira']['base_url']}/rest/api/3/issue"
            response = requests.post(url, headers=self.jira_headers, auth=self.jira_auth, 
                                   data=json.dumps(issue_data))
            response.raise_for_status()
            
            created_issue = response.json()
            issue_key = created_issue['key']
            
            logger.info(f"Created Jira issue {issue_key} for Aha! idea '{idea.get('name', 'Untitled')}'")
            
            # Add web link if URL is available
            if idea.get('url'):
                self.add_web_link_to_jira_issue(issue_key, idea['url'], f"Aha! Idea: {idea.get('name', 'Untitled')}")
            
            return issue_key
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Jira issue for idea '{idea.get('name', 'Untitled')}': {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
    
    def get_nested_field_value(self, data: Dict, field_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                try:
                    current = current[int(key)]
                except (IndexError, ValueError):
                    return None
            else:
                return None
        
        return current
    
    def sync_ideas(self, product_id: str) -> Dict[str, Any]:
        """Main sync function"""
        logger.info("Starting Aha! to Jira sync")
        
        results = {
            'total_ideas': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'errors': []
        }
        
        try:
            # Fetch all ideas
            ideas_list = self.fetch_ideas_list(product_id)
            results['total_ideas'] = len(ideas_list)
            
            # Process each idea
            for idea_summary in ideas_list:
                idea_id = idea_summary['id']
                
                try:
                    # Fetch detailed idea information
                    detailed_idea = self.fetch_idea_details(idea_id)
                    
                    # Fetch comments for the idea
                    comments = self.fetch_idea_comments(idea_id)
                    
                    # Create Jira issue
                    jira_issue_key = self.create_jira_issue(detailed_idea)
                    
                    if jira_issue_key:
                        # Add comments if any exist
                        if comments:
                            formatted_comments = self.format_comments_for_jira(comments)
                            self.add_comment_to_jira_issue(jira_issue_key, formatted_comments)
                        
                        results['successful_syncs'] += 1
                    else:
                        results['failed_syncs'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing idea {idea_id}: {e}")
                    results['failed_syncs'] += 1
                    results['errors'].append(f"Idea {idea_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Fatal error during sync: {e}")
            results['errors'].append(f"Fatal error: {str(e)}")
        
        logger.info(f"Sync completed. Success: {results['successful_syncs']}, "
                   f"Failed: {results['failed_syncs']}, Total: {results['total_ideas']}")
        
        return results

def load_config(config_file: str = 'config.json') -> Dict[str, Any]:
    """Load configuration from file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "aha": {
            "base_url": "https://your-company.aha.io",
            "api_token": "your-aha-api-token"
        },
        "jira": {
            "base_url": "https://your-company.atlassian.net",
            "username": "your-email@company.com",
            "api_token": "your-jira-api-token",
            "project_key": "PROJ",
            "issue_type": "Story",
            "default_status": "To Do"
        },
        "field_mappings": {
            "assignee_mappings": {
                "aha-user@company.com": "jira-user@company.com"
            },
            "status_mappings": {
                "New": "To Do",
                "Under review": "In Progress",
                "Approved": "To Do",
                "Shipped": "Done"
            },
            "priority_mappings": {
                "high": "High",
                "medium": "Medium",
                "low": "Low"
            },
            "custom_fields": {
                "custom_field_name": "customfield_10001"
            }
        }
    }
    
    with open('config.sample.json', 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print("Sample configuration created: config.sample.json")
    print("Please copy it to config.json and update with your actual values")

def inspect_idea_fields(config_file: str = 'config.json', product_id: str = None):
    """Inspect available custom fields in Aha! ideas for mapping configuration"""
    try:
        config = load_config(config_file)
        sync_tool = AhaJiraSync(config)
        
        if not product_id:
            product_id = input("Enter Aha! Product ID: ").strip()
        
        print("Fetching ideas to analyze available fields...")
        ideas_list = sync_tool.fetch_ideas_list(product_id)
        
        if not ideas_list:
            print("No ideas found for the specified product.")
            return
        
        # Analyze first few ideas to get field structure
        sample_size = min(5, len(ideas_list))
        all_custom_fields = set()
        all_standard_fields = set()
        
        print(f"\nAnalyzing {sample_size} ideas for available fields...\n")
        
        for i in range(sample_size):
            idea_summary = ideas_list[i]
            detailed_idea = sync_tool.fetch_idea_details(idea_summary['id'])
            
            # Collect standard fields
            for key in detailed_idea.keys():
                all_standard_fields.add(key)
            
            # Collect custom fields
            if detailed_idea.get('custom_fields'):
                for field in detailed_idea['custom_fields']:
                    field_name = field.get('name')
                    if field_name:
                        all_custom_fields.add(field_name)
        
        print("=== AVAILABLE STANDARD FIELDS ===")
        for field in sorted(all_standard_fields):
            print(f"  - {field}")
        
        print(f"\n=== AVAILABLE CUSTOM FIELDS ({len(all_custom_fields)} found) ===")
        for field in sorted(all_custom_fields):
            print(f"  - {field}")
        
        print("\n=== CONFIGURATION EXAMPLES ===")
        print("Add these to your config.json under field_mappings:")
        print()
        print('"description_custom_fields": [')
        for field in sorted(list(all_custom_fields)[:3]):  # Show first 3 as examples
            print(f'    "{field}",')
        print('    ...'),
        print('],')
        print()
        print('"custom_fields": {')
        for field in sorted(list(all_custom_fields)[:3]):  # Show first 3 as examples
            field_id = field.replace(' ', '_').lower()
            print(f'    "custom_fields.{field}": "customfield_10XXX",  // Map to your Jira field')
        print('    ...'),
        print('}')
        
        # Show sample idea structure
        if ideas_list:
            print(f"\n=== SAMPLE IDEA STRUCTURE ===")
            sample_idea = sync_tool.fetch_idea_details(ideas_list[0]['id'])
            print("First idea structure (truncated):")
            
            # Create a simplified view
            simplified = {
                'id': sample_idea.get('id'),
                'name': sample_idea.get('name'),
                'reference_num': sample_idea.get('reference_num'),
                'url': sample_idea.get('url'),
                'created_at': sample_idea.get('created_at'),
                'created_by': sample_idea.get('created_by', {}).get('email') if sample_idea.get('created_by') else None,
                'custom_fields_sample': [
                    {'name': cf.get('name'), 'type': type(cf.get('value', '')).__name__} 
                    for cf in (sample_idea.get('custom_fields', [])[:3])
                ],
                'feature': sample_idea.get('feature', {}).get('reference_num') if sample_idea.get('feature') else None
            }
            
            print(json.dumps(simplified, indent=2))
    
    except Exception as e:
        logger.error(f"Error inspecting fields: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--create-config':
        create_sample_config()
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-fields':
        product_id = sys.argv[2] if len(sys.argv) > 2 else None
        inspect_idea_fields(product_id=product_id)
        return
    
    try:
        config = load_config()
        
        # Get product ID from command line or config
        if len(sys.argv) > 1:
            product_id = sys.argv[1]
        else:
            product_id = config.get('aha', {}).get('product_id')
            
        if not product_id:
            logger.error("Product ID not provided. Use: python script.py <product_id>")
            return
        
        # Initialize and run sync
        sync_tool = AhaJiraSync(config)
        results = sync_tool.sync_ideas(product_id)
        
        # Print summary
        print("\n" + "="*50)
        print("SYNC SUMMARY")
        print("="*50)
        print(f"Total ideas processed: {results['total_ideas']}")
        print(f"Successfully synced: {results['successful_syncs']}")
        print(f"Failed to sync: {results['failed_syncs']}")
        
        if results['errors']:
            print("\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")
                
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
