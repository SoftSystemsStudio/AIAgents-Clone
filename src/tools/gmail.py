"""
Gmail Tools - Email management and cleanup operations.

Provides tools for:
- Reading emails (inbox, unread, by sender)
- Deleting emails (bulk operations)
- Archiving and labeling
- Searching and filtering
- Unsubscribing from lists
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import base64
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    import os.path
except ImportError:
    raise ImportError(
        "Gmail tools require Google API packages. Install with:\n"
        "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )

from src.domain.models import Tool, ToolParameter


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly',
]


class GmailClient:
    """
    Gmail API client wrapper.
    
    Handles authentication and provides methods for email operations.
    """
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to store authentication token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Load saved credentials
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}\n"
                        "Follow these steps:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Create a new project or select existing\n"
                        "3. Enable Gmail API\n"
                        "4. Create OAuth 2.0 credentials (Desktop app)\n"
                        "5. Download credentials.json to project root"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def list_messages(
        self,
        query: str = '',
        max_results: int = 100,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List messages matching query.
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            max_results: Maximum messages to return
            label_ids: Filter by label IDs
            
        Returns:
            List of message metadata
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results,
                labelIds=label_ids,
            ).execute()
            
            return results.get('messages', [])
        except Exception as e:
            raise Exception(f"Failed to list messages: {str(e)}")
    
    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get full message details."""
        try:
            return self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full',
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to get message {message_id}: {str(e)}")
    
    def delete_message(self, message_id: str) -> None:
        """Permanently delete a message."""
        try:
            self.service.users().messages().delete(
                userId='me',
                id=message_id,
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to delete message {message_id}: {str(e)}")
    
    def trash_message(self, message_id: str) -> None:
        """Move message to trash."""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id,
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to trash message {message_id}: {str(e)}")
    
    def modify_message(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> None:
        """Modify message labels."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': add_labels or [],
                    'removeLabelIds': remove_labels or [],
                },
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to modify message {message_id}: {str(e)}")
    
    def batch_delete(self, message_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple messages."""
        try:
            self.service.users().messages().batchDelete(
                userId='me',
                body={'ids': message_ids},
            ).execute()
            return {"deleted": len(message_ids)}
        except Exception as e:
            raise Exception(f"Failed to batch delete: {str(e)}")


def create_gmail_tools(credentials_path: str = 'credentials.json') -> List[Tool]:
    """
    Create Gmail management tools.
    
    Args:
        credentials_path: Path to Gmail OAuth credentials
        
    Returns:
        List of Gmail tools
    """
    client = GmailClient(credentials_path)
    
    async def list_emails(
        query: str = "is:unread",
        max_results: int = 50,
    ) -> str:
        """
        List emails matching query.
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:notifications@', 'older_than:30d')
            max_results: Maximum emails to return (default: 50)
            
        Returns:
            Summary of matching emails
        """
        messages = client.list_messages(query=query, max_results=max_results)
        
        if not messages:
            return f"No emails found matching query: {query}"
        
        # Get details for each message
        email_summaries = []
        for msg in messages[:20]:  # Show first 20 in detail
            try:
                details = client.get_message(msg['id'])
                headers = {h['name']: h['value'] for h in details['payload']['headers']}
                
                email_summaries.append({
                    'id': msg['id'],
                    'from': headers.get('From', 'Unknown'),
                    'subject': headers.get('Subject', 'No subject'),
                    'date': headers.get('Date', 'Unknown'),
                    'snippet': details.get('snippet', '')[:100],
                })
            except Exception as e:
                email_summaries.append({
                    'id': msg['id'],
                    'error': str(e),
                })
        
        # Format response
        response = f"Found {len(messages)} emails matching '{query}':\n\n"
        for idx, email in enumerate(email_summaries, 1):
            if 'error' in email:
                response += f"{idx}. ID: {email['id']} (Error: {email['error']})\n"
            else:
                response += f"{idx}. From: {email['from']}\n"
                response += f"   Subject: {email['subject']}\n"
                response += f"   Date: {email['date']}\n"
                response += f"   Snippet: {email['snippet']}...\n"
                response += f"   ID: {email['id']}\n\n"
        
        if len(messages) > 20:
            response += f"\n... and {len(messages) - 20} more emails."
        
        return response
    
    async def delete_emails_by_sender(sender: str, max_delete: int = 100) -> str:
        """
        Delete all emails from a specific sender.
        
        Args:
            sender: Email address or domain to delete (e.g., 'notifications@example.com' or '@promotions.com')
            max_delete: Maximum emails to delete (safety limit, default: 100)
            
        Returns:
            Deletion summary
        """
        query = f"from:{sender}"
        messages = client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found from sender: {sender}"
        
        # Get count
        count = len(messages)
        
        # Delete in batches
        message_ids = [msg['id'] for msg in messages]
        client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails from {sender}"
    
    async def delete_old_emails(days: int = 30, max_delete: int = 200) -> str:
        """
        Delete emails older than specified days.
        
        Args:
            days: Delete emails older than this many days (default: 30)
            max_delete: Maximum emails to delete (default: 200)
            
        Returns:
            Deletion summary
        """
        query = f"older_than:{days}d"
        messages = client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found older than {days} days"
        
        count = len(messages)
        message_ids = [msg['id'] for msg in messages]
        client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails older than {days} days"
    
    async def archive_emails_by_sender(sender: str, max_archive: int = 100) -> str:
        """
        Archive (remove from inbox) all emails from a sender.
        
        Args:
            sender: Email address or domain
            max_archive: Maximum emails to archive (default: 100)
            
        Returns:
            Archive summary
        """
        query = f"from:{sender} in:inbox"
        messages = client.list_messages(query=query, max_results=max_archive)
        
        if not messages:
            return f"No inbox emails found from sender: {sender}"
        
        # Archive by removing INBOX label
        count = 0
        for msg in messages:
            try:
                client.modify_message(msg['id'], remove_labels=['INBOX'])
                count += 1
            except Exception as e:
                pass
        
        return f"Successfully archived {count} emails from {sender}"
    
    async def search_and_delete(
        search_term: str,
        confirm: bool = True,
        max_delete: int = 50,
    ) -> str:
        """
        Search for emails and delete them.
        
        Args:
            search_term: Search query (subject, content, etc.)
            confirm: Must be True to actually delete (safety check)
            max_delete: Maximum to delete (default: 50)
            
        Returns:
            Deletion summary
        """
        if not confirm:
            return "Error: Must set confirm=True to delete emails. Search first with list_emails."
        
        query = f"subject:({search_term}) OR {search_term}"
        messages = client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found matching: {search_term}"
        
        count = len(messages)
        message_ids = [msg['id'] for msg in messages]
        client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails matching '{search_term}'"
    
    # Create tool definitions
    tools = [
        Tool(
            name="list_emails",
            description="List emails in Gmail inbox. Can filter by query (is:unread, from:sender, older_than:Xd, etc.)",
            function=list_emails,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Gmail search query (e.g., 'is:unread', 'from:notifications@', 'older_than:30d')",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum emails to return (default: 50)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="delete_emails_by_sender",
            description="Delete all emails from a specific sender or domain",
            function=delete_emails_by_sender,
            parameters=[
                ToolParameter(
                    name="sender",
                    type="string",
                    description="Email address or domain (e.g., 'spam@example.com' or '@promotions.com')",
                    required=True,
                ),
                ToolParameter(
                    name="max_delete",
                    type="integer",
                    description="Maximum emails to delete (safety limit, default: 100)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="delete_old_emails",
            description="Delete emails older than specified number of days",
            function=delete_old_emails,
            parameters=[
                ToolParameter(
                    name="days",
                    type="integer",
                    description="Delete emails older than this many days (default: 30)",
                    required=False,
                ),
                ToolParameter(
                    name="max_delete",
                    type="integer",
                    description="Maximum emails to delete (default: 200)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="archive_emails_by_sender",
            description="Archive (remove from inbox without deleting) emails from a sender",
            function=archive_emails_by_sender,
            parameters=[
                ToolParameter(
                    name="sender",
                    type="string",
                    description="Email address or domain to archive",
                    required=True,
                ),
                ToolParameter(
                    name="max_archive",
                    type="integer",
                    description="Maximum emails to archive (default: 100)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="search_and_delete",
            description="Search for emails by subject/content and delete them (requires confirmation)",
            function=search_and_delete,
            parameters=[
                ToolParameter(
                    name="search_term",
                    type="string",
                    description="Search term to find in subject or body",
                    required=True,
                ),
                ToolParameter(
                    name="confirm",
                    type="boolean",
                    description="Must be true to actually delete (safety check)",
                    required=True,
                ),
                ToolParameter(
                    name="max_delete",
                    type="integer",
                    description="Maximum to delete (default: 50)",
                    required=False,
                ),
            ],
        ),
    ]
    
    return tools
