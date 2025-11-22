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
    'https://www.googleapis.com/auth/gmail.modify',  # Read, compose, send, and modify emails
    'https://www.googleapis.com/auth/gmail.readonly',  # View emails and settings
    # Note: gmail.modify does NOT include permission to permanently delete emails
    # For batch delete to work, you need one of these additional scopes:
    # - https://mail.google.com/ (full Gmail access)
    # We'll use trash_message instead of permanent delete for safety
]

# Global client instance (initialized when tools are created)
_gmail_client: Optional['GmailClient'] = None


def get_gmail_client() -> 'GmailClient':
    """Get the global Gmail client instance."""
    if _gmail_client is None:
        raise RuntimeError("Gmail client not initialized. Call create_gmail_tools() first.")
    return _gmail_client


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
                
                # Use out-of-band (OOB) flow for cloud environments
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                print("\n🔐 Gmail Authentication Required")
                print("=" * 60)
                print("STEP 1: Copy the URL below and open it in your browser")
                print("STEP 2: Sign in and grant permissions")
                print("STEP 3: Google will show you an authorization code")
                print("STEP 4: Copy that code and paste it back here")
                print("=" * 60)
                print()
                
                # Generate authorization URL with OOB redirect
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Authorization URL:\n{auth_url}\n")
                
                # Get code from user
                code = input("Enter the authorization code: ").strip()
                
                flow.fetch_token(code=code)
                creds = flow.credentials
            
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
        List messages matching query with pagination support.
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            max_results: Maximum messages to return (will paginate if needed)
            label_ids: Filter by label IDs
            
        Returns:
            List of message metadata
        """
        try:
            all_messages = []
            page_token = None
            
            while True:
                # Gmail API max is 500 per request
                remaining = max_results - len(all_messages) if max_results else 500
                page_size = min(500, remaining) if max_results else 500
                
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=page_size,
                    labelIds=label_ids,
                    pageToken=page_token,
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                
                all_messages.extend(messages)
                
                # Check if we've reached the limit or no more pages
                page_token = results.get('nextPageToken')
                if not page_token or (max_results and len(all_messages) >= max_results):
                    break
            
            return all_messages
        except Exception as e:
            raise Exception(f"Failed to list messages: {str(e)}")
    
    def count_messages(self, query: str = '', max_count: int = 10000) -> int:
        """
        Count total messages matching query by paginating through results.
        More accurate than Gmail's resultSizeEstimate which can be very wrong.
        
        Args:
            query: Gmail search query
            max_count: Maximum messages to count (default 10000 to avoid long waits)
            
        Returns:
            Actual count of matching messages (up to max_count)
        """
        try:
            total = 0
            page_token = None
            
            while total < max_count:
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=500,  # Max per page
                    pageToken=page_token,
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                
                total += len(messages)
                
                # Check if there are more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return total
        except Exception as e:
            raise Exception(f"Failed to count messages: {str(e)}")
    
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
        """Move multiple messages to trash (safer than permanent delete)."""
        try:
            count = 0
            for msg_id in message_ids:
                try:
                    self.trash_message(msg_id)
                    count += 1
                except Exception:
                    pass  # Continue with other messages
            return {"deleted": count}
        except Exception as e:
            raise Exception(f"Failed to trash messages: {str(e)}")


# ============================================================================
# Tool Handler Functions (module-level for registry)
# ============================================================================

async def list_emails(query: str = "is:unread", max_results: int = 20) -> str:
    """List emails matching query."""
    client = get_gmail_client()
    
    # Get count using Gmail's estimate (fast and accurate)
    total_count = _gmail_client.count_messages(query=query)
    
    if total_count == 0:
        return f"No emails found matching query: {query}"
    
    # Then get details for display (limited)
    messages = _gmail_client.list_messages(query=query, max_results=max_results)
    
    # Get details for each message
    email_summaries = []
    for msg in messages:
        try:
            details = _gmail_client.get_message(msg['id'])
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
    
    # Format response with total count
    response = f"Found {total_count} emails matching '{query}':\n\n"
    for idx, email in enumerate(email_summaries, 1):
        if 'error' in email:
            response += f"{idx}. ID: {email['id']} (Error: {email['error']})\n"
        else:
            response += f"{idx}. From: {email['from']}\n"
            response += f"   Subject: {email['subject']}\n"
            response += f"   Date: {email['date']}\n"
            response += f"   Snippet: {email['snippet']}...\n"
            response += f"   ID: {email['id']}\n\n"
    
    if total_count > len(email_summaries):
        response += f"\n... and {total_count - len(email_summaries)} more emails."
    
    return response


async def delete_emails_by_sender(sender: str, max_delete: int = 500) -> str:
    """Delete (move to trash) all emails from a specific sender."""
    client = get_gmail_client()
    query = f"from:{sender}"
    messages = _gmail_client.list_messages(query=query, max_results=max_delete)
    
    if not messages:
        return f"No emails found from sender: {sender}"
    
    count = len(messages)
    message_ids = [msg['id'] for msg in messages]
    result = _gmail_client.batch_delete(message_ids)
    
    return f"Successfully moved {result['deleted']} emails from {sender} to trash"


async def delete_old_emails(days: int = 30, max_delete: int = 1000) -> str:
    """Delete (move to trash) emails older than specified days."""
    client = get_gmail_client()
    query = f"older_than:{days}d"
    messages = _gmail_client.list_messages(query=query, max_results=max_delete)
    
    if not messages:
        return f"No emails found older than {days} days"
    
    count = len(messages)
    message_ids = [msg['id'] for msg in messages]
    result = _gmail_client.batch_delete(message_ids)
    
    return f"Successfully moved {result['deleted']} emails older than {days} days to trash"


async def archive_emails_by_sender(sender: str, max_archive: int = 500) -> str:
    """Archive (remove from inbox) emails from a sender."""
    client = get_gmail_client()
    query = f"from:{sender}"
    messages = _gmail_client.list_messages(query=query, max_results=max_archive)
    
    if not messages:
        return f"No emails found from sender: {sender}"
    
    count = len(messages)
    for msg in messages:
        _gmail_client.modify_message(msg['id'], remove_labels=['INBOX'])
    
    return f"Successfully archived {count} emails from {sender}"


async def search_and_delete(search_term: str, confirm: bool, max_delete: int = 500) -> str:
    """Search for emails and delete them (move to trash)."""
    if not confirm:
        return "Error: Must set confirm=True to delete emails (safety check)"
    
    client = get_gmail_client()
    query = f"subject:({search_term}) OR {search_term}"
    messages = _gmail_client.list_messages(query=query, max_results=max_delete)
    
    if not messages:
        return f"No emails found matching '{search_term}'"
    
    count = len(messages)
    message_ids = [msg['id'] for msg in messages]
    result = _gmail_client.batch_delete(message_ids)
    
    return f"Successfully moved {result['deleted']} emails matching '{search_term}' to trash"


# ============================================================================
# Tool Factory
# ============================================================================

def create_gmail_tools(credentials_path: str = 'credentials.json') -> List[Tool]:
    """
    Create Gmail management tools.
    
    Args:
        credentials_path: Path to Gmail OAuth credentials
        
    Returns:
        List of Gmail tools
    """
    global _gmail_client
    _gmail_client = GmailClient(credentials_path)
    
    async def list_emails(
        query: str = "is:unread",
        max_results: int = 20,
    ) -> str:
        """
        List emails matching query.
        
        Args:
            query: Gmail search query (default: 'is:unread' for ALL unread. Use 'is:unread in:inbox' for inbox only, 'from:sender@', 'older_than:30d', etc.)
            max_results: Maximum emails to show details for (default: 20)
            
        Returns:
            Summary of matching emails with total count
        """
        # Get total count using Gmail's estimate
        total_count = _gmail_client.count_messages(query=query)
        
        if total_count == 0:
            return f"No emails found matching query: {query}"
        
        # Get details for display (limited)
        messages = _gmail_client.list_messages(query=query, max_results=max_results)
        
        # Get details for each message
        email_summaries = []
        for msg in messages:
            try:
                details = _gmail_client.get_message(msg['id'])
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
        
        # Format response with accurate total count
        response = f"Found {total_count} emails matching '{query}':\n\n"
        for idx, email in enumerate(email_summaries, 1):
            if 'error' in email:
                response += f"{idx}. ID: {email['id']} (Error: {email['error']})\n"
            else:
                response += f"{idx}. From: {email['from']}\n"
                response += f"   Subject: {email['subject']}\n"
                response += f"   Date: {email['date']}\n"
                response += f"   Snippet: {email['snippet']}...\n"
                response += f"   ID: {email['id']}\n\n"
        
        if total_count > len(email_summaries):
            response += f"\n... and {total_count - len(email_summaries)} more emails."
        
        return response
    
    async def delete_emails_by_sender(sender: str, max_delete: int = 500) -> str:
        """
        Delete all emails from a specific sender.
        
        Args:
            sender: Email address or domain to delete (e.g., 'notifications@example.com' or '@promotions.com')
            max_delete: Maximum emails to delete (safety limit, default: 100)
            
        Returns:
            Deletion summary
        """
        query = f"from:{sender}"
        messages = _gmail_client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found from sender: {sender}"
        
        # Get count
        count = len(messages)
        
        # Delete in batches
        message_ids = [msg['id'] for msg in messages]
        _gmail_client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails from {sender}"
    
    async def delete_old_emails(days: int = 30, max_delete: int = 1000) -> str:
        """
        Delete emails older than specified days.
        
        Args:
            days: Delete emails older than this many days (default: 30)
            max_delete: Maximum emails to delete (default: 200)
            
        Returns:
            Deletion summary
        """
        query = f"older_than:{days}d"
        messages = _gmail_client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found older than {days} days"
        
        count = len(messages)
        message_ids = [msg['id'] for msg in messages]
        _gmail_client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails older than {days} days"
    
    async def archive_emails_by_sender(sender: str, max_archive: int = 500) -> str:
        """
        Archive (remove from inbox) all emails from a sender.
        
        Args:
            sender: Email address or domain
            max_archive: Maximum emails to archive (default: 100)
            
        Returns:
            Archive summary
        """
        query = f"from:{sender} in:inbox"
        messages = _gmail_client.list_messages(query=query, max_results=max_archive)
        
        if not messages:
            return f"No inbox emails found from sender: {sender}"
        
        # Archive by removing INBOX label
        count = 0
        for msg in messages:
            try:
                _gmail_client.modify_message(msg['id'], remove_labels=['INBOX'])
                count += 1
            except Exception as e:
                pass
        
        return f"Successfully archived {count} emails from {sender}"
    
    async def search_and_delete(
        search_term: str,
        confirm: bool,
        max_delete: int = 500,
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
        messages = _gmail_client.list_messages(query=query, max_results=max_delete)
        
        if not messages:
            return f"No emails found matching: {search_term}"
        
        count = len(messages)
        message_ids = [msg['id'] for msg in messages]
        _gmail_client.batch_delete(message_ids)
        
        return f"Successfully deleted {count} emails matching '{search_term}'"
    
    # Create tool definitions
    tools = [
        Tool(
            name="list_emails",
            description="List emails in Gmail inbox. Can filter by query (is:unread, from:sender, older_than:Xd, etc.)",
            handler_module="src.tools.gmail",
            handler_function="list_emails",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Gmail search query (default: 'is:unread' for ALL unread emails. Use 'is:unread in:inbox' for inbox only, 'from:sender@', 'older_than:30d', etc.)",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum emails to show details for (default: 20)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="delete_emails_by_sender",
            description="Delete all emails from a specific sender or domain",
            handler_module="src.tools.gmail",
            handler_function="delete_emails_by_sender",
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
                    description="Maximum emails to delete (safety limit, default: 500)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="delete_old_emails",
            description="Delete emails older than specified number of days",
            handler_module="src.tools.gmail",
            handler_function="delete_old_emails",
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
                    description="Maximum emails to delete (default: 1000)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="archive_emails_by_sender",
            description="Archive (remove from inbox without deleting) emails from a sender",
            handler_module="src.tools.gmail",
            handler_function="archive_emails_by_sender",
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
                    description="Maximum emails to archive (default: 500)",
                    required=False,
                ),
            ],
        ),
        Tool(
            name="search_and_delete",
            description="Search for emails by subject/content and delete them (requires confirmation)",
            handler_module="src.tools.gmail",
            handler_function="search_and_delete",
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
                    description="Maximum to delete (default: 500)",
                    required=False,
                ),
            ],
        ),
    ]
    
    return tools
