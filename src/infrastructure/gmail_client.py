"""
Gmail Client Infrastructure - Gmail API adapter.

Provides clean interface to Gmail API, returning domain entities
instead of raw API responses. Implements IGmailClient interface.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import contextlib
import importlib.util
import os.path
import pickle

from src.domain.email_thread import (
    EmailMessage,
    EmailThread,
    EmailAddress,
    EmailCategory,
    EmailImportance,
)
from src.domain.gmail_interfaces import IGmailClient


def _google_packages_available() -> bool:
    with contextlib.suppress(ModuleNotFoundError):
        return importlib.util.find_spec("google.oauth2.credentials") is not None
    return False


if _google_packages_available():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    _GOOGLE_PACKAGES_AVAILABLE = True
else:  # pragma: no cover - executed only when dependencies missing
    Credentials = None  # type: ignore[assignment]
    InstalledAppFlow = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]
    build = None  # type: ignore[assignment]

    _GOOGLE_PACKAGES_AVAILABLE = False

# Gmail API scopes - modify allows read/write but not permanent delete
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly',
]


class GmailClient(IGmailClient):
    """
    Gmail API client that returns domain entities.
    
    Handles OAuth, pagination, and API interactions, returning
    rich domain objects instead of raw API responses.
    """
    
    def __init__(
        self,
        credentials_path: str = 'credentials.json',
        token_path: str = 'token.pickle'
    ):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to store authentication token
        """
        if not _GOOGLE_PACKAGES_AVAILABLE:
            raise ImportError(
                "Gmail client requires Google API packages. Install with:\n"
                "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )

        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
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
                        "Follow setup instructions in docs/GMAIL_SETUP.md"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                
                # Use out-of-band (OOB) flow for cloud environments
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                print("\n🔐 Gmail Authentication Required")
                print("=" * 60)
                print("1. Copy the URL below and open it in your browser")
                print("2. Sign in and grant permissions")
                print("3. Copy the authorization code from Google")
                print("4. Paste it back here")
                print("=" * 60)
                print()
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Authorization URL:\n{auth_url}\n")
                
                code = input("Enter the authorization code: ").strip()
                
                flow.fetch_token(code=code)
                creds = flow.credentials
            
            # Save credentials
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def _parse_email_address(self, raw: str) -> EmailAddress:
        """Parse email address from Gmail header format."""
        # Format: "Name <email@domain.com>" or just "email@domain.com"
        if '<' in raw and '>' in raw:
            name = raw.split('<')[0].strip().strip('"')
            address = raw.split('<')[1].split('>')[0].strip()
        else:
            name = ""
            address = raw.strip()
        
        return EmailAddress(address=address, name=name)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Gmail date string to datetime."""
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.utcnow()
    
    def _message_to_domain(self, msg_data: Dict[str, Any]) -> EmailMessage:
        """Convert Gmail API message to domain EmailMessage."""
        headers = {h['name']: h['value'] 
                  for h in msg_data['payload']['headers']}
        
        # Parse basic fields
        message_id = msg_data['id']
        thread_id = msg_data['threadId']
        from_address = self._parse_email_address(headers.get('From', 'unknown@unknown.com'))
        to_addresses = [self._parse_email_address(addr.strip()) 
                       for addr in headers.get('To', '').split(',') if addr.strip()]
        cc_addresses = [self._parse_email_address(addr.strip()) 
                       for addr in headers.get('Cc', '').split(',') if addr.strip()]
        subject = headers.get('Subject', '(No subject)')
        date = self._parse_date(headers.get('Date', ''))
        snippet = msg_data.get('snippet', '')
        labels = msg_data.get('labelIds', [])
        
        # Determine category from labels
        category = EmailCategory.UNKNOWN
        if 'CATEGORY_SOCIAL' in labels:
            category = EmailCategory.SOCIAL
        elif 'CATEGORY_PROMOTIONS' in labels:
            category = EmailCategory.PROMOTIONS
        elif 'CATEGORY_UPDATES' in labels:
            category = EmailCategory.UPDATES
        elif 'CATEGORY_FORUMS' in labels:
            category = EmailCategory.FORUMS
        elif 'INBOX' in labels or 'CATEGORY_PRIMARY' in labels:
            category = EmailCategory.PRIMARY
        
        # Determine importance (simplified heuristic)
        importance = EmailImportance.MEDIUM
        if 'IMPORTANT' in labels or 'STARRED' in labels:
            importance = EmailImportance.HIGH
        elif 'SPAM' in labels:
            importance = EmailImportance.SPAM
        elif category == EmailCategory.PROMOTIONS:
            importance = EmailImportance.LOW
        
        # Parse flags
        is_unread = 'UNREAD' in labels
        is_starred = 'STARRED' in labels
        has_attachments = 'parts' in msg_data['payload']
        
        # Size in bytes
        size_bytes = int(msg_data.get('sizeEstimate', 0))
        
        return EmailMessage(
            id=message_id,
            thread_id=thread_id,
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=subject,
            snippet=snippet,
            date=date,
            labels=labels,
            is_unread=is_unread,
            is_starred=is_starred,
            has_attachments=has_attachments,
            size_bytes=size_bytes,
            category=category,
            importance=importance,
        )
    
    def get_message(self, message_id: str) -> EmailMessage:
        """
        Get full message by ID.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            EmailMessage domain entity
        """
        try:
            msg_data = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full',
            ).execute()
            
            return self._message_to_domain(msg_data)
        except Exception as e:
            raise Exception(f"Failed to get message {message_id}: {str(e)}")
    
    def list_messages(
        self,
        query: str = '',
        max_results: Optional[int] = None,
        label_ids: Optional[List[str]] = None,
    ) -> List[EmailMessage]:
        """
        List messages matching query.
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            max_results: Maximum messages to return (will paginate if needed)
            label_ids: Filter by label IDs
            
        Returns:
            List of EmailMessage domain entities
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
                
                # Fetch full message details for each
                for msg_ref in messages:
                    msg = self.get_message(msg_ref['id'])
                    all_messages.append(msg)
                
                # Check if we've reached the limit or no more pages
                page_token = results.get('nextPageToken')
                if not page_token or (max_results and len(all_messages) >= max_results):
                    break
            
            return all_messages
        except Exception as e:
            raise Exception(f"Failed to list messages: {str(e)}")
    
    def count_messages(self, query: str = '', max_count: int = 10000) -> int:
        """
        Count total messages matching query.
        
        More accurate than Gmail's resultSizeEstimate.
        
        Args:
            query: Gmail search query
            max_count: Maximum messages to count (to avoid long waits)
            
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
                    maxResults=500,
                    pageToken=page_token,
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                
                total += len(messages)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return total
        except Exception as e:
            raise Exception(f"Failed to count messages: {str(e)}")
    
    def get_thread(self, thread_id: str) -> EmailThread:
        """
        Get complete thread with all messages.
        
        Args:
            thread_id: Gmail thread ID
            
        Returns:
            EmailThread domain entity
        """
        try:
            thread_data = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full',
            ).execute()
            
            messages = [self._message_to_domain(msg) 
                       for msg in thread_data.get('messages', [])]
            
            return EmailThread(
                id=thread_id,
                messages=messages,
            )
        except Exception as e:
            raise Exception(f"Failed to get thread {thread_id}: {str(e)}")
    
    def list_threads(
        self,
        query: str = '',
        max_results: Optional[int] = None,
    ) -> List[EmailThread]:
        """
        List threads matching query.
        
        Args:
            query: Gmail search query
            max_results: Maximum threads to return
            
        Returns:
            List of EmailThread domain entities
        """
        try:
            all_threads = []
            page_token = None
            
            while True:
                remaining = max_results - len(all_threads) if max_results else 100
                page_size = min(100, remaining) if max_results else 100
                
                results = self.service.users().threads().list(
                    userId='me',
                    q=query,
                    maxResults=page_size,
                    pageToken=page_token,
                ).execute()
                
                threads = results.get('threads', [])
                if not threads:
                    break
                
                # Fetch full thread details
                for thread_ref in threads:
                    thread = self.get_thread(thread_ref['id'])
                    all_threads.append(thread)
                
                page_token = results.get('nextPageToken')
                if not page_token or (max_results and len(all_threads) >= max_results):
                    break
            
            return all_threads
        except Exception as e:
            raise Exception(f"Failed to list threads: {str(e)}")
    
    def trash_message(self, message_id: str) -> None:
        """
        Move message to trash.
        
        Args:
            message_id: Gmail message ID
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id,
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to trash message {message_id}: {str(e)}")
    
    def trash_messages(self, message_ids: List[str]) -> int:
        """
        Move multiple messages to trash.
        
        Args:
            message_ids: List of Gmail message IDs
            
        Returns:
            Count of successfully trashed messages
        """
        count = 0
        for msg_id in message_ids:
            try:
                self.trash_message(msg_id)
                count += 1
            except Exception:
                pass  # Continue with remaining messages
        return count
    
    def modify_labels(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> None:
        """
        Modify message labels.
        
        Args:
            message_id: Gmail message ID
            add_labels: Labels to add
            remove_labels: Labels to remove
        """
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
    
    def archive_message(self, message_id: str) -> None:
        """
        Archive message (remove from inbox).
        
        Args:
            message_id: Gmail message ID
        """
        self.modify_labels(message_id, remove_labels=['INBOX'])
    
    def archive_messages(self, message_ids: List[str]) -> int:
        """
        Archive multiple messages.
        
        Args:
            message_ids: List of Gmail message IDs
            
        Returns:
            Count of successfully archived messages
        """
        count = 0
        for msg_id in message_ids:
            try:
                self.archive_message(msg_id)
                count += 1
            except Exception:
                pass
        return count
    
    def mark_read(self, message_id: str) -> None:
        """Mark message as read."""
        self.modify_labels(message_id, remove_labels=['UNREAD'])
    
    def mark_unread(self, message_id: str) -> None:
        """Mark message as unread."""
        self.modify_labels(message_id, add_labels=['UNREAD'])
    
    def star_message(self, message_id: str) -> None:
        """Star message."""
        self.modify_labels(message_id, add_labels=['STARRED'])
    
    def unstar_message(self, message_id: str) -> None:
        """Unstar message."""
        self.modify_labels(message_id, remove_labels=['STARRED'])
    
    def batch_modify_messages(
        self,
        message_ids: List[str],
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Batch modify multiple messages.
        
        Uses Gmail API batch request for efficiency.
        
        Args:
            message_ids: List of message IDs
            add_labels: Labels to add
            remove_labels: Labels to remove
            
        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}
        
        # Gmail API supports batch requests via batchModify
        try:
            self.service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': message_ids,
                    'addLabelIds': add_labels or [],
                    'removeLabelIds': remove_labels or [],
                },
            ).execute()
            results['success'] = len(message_ids)
        except Exception as e:
            # Fall back to individual modifications if batch fails
            for msg_id in message_ids:
                try:
                    self.modify_labels(msg_id, add_labels, remove_labels)
                    results['success'] += 1
                except Exception:
                    results['failed'] += 1
        
        return results
    
    def batch_archive_messages(self, message_ids: List[str]) -> Dict[str, int]:
        """
        Archive multiple messages in batch.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            Dict with 'success' and 'failed' counts
        """
        return self.batch_modify_messages(message_ids, remove_labels=['INBOX'])
    
    def batch_trash_messages(self, message_ids: List[str]) -> Dict[str, int]:
        """
        Trash multiple messages in batch.
        
        Note: Gmail API doesn't have batch trash, so this falls back
        to individual trash operations with progress tracking.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}
        
        for msg_id in message_ids:
            try:
                self.trash_message(msg_id)
                results['success'] += 1
            except Exception:
                results['failed'] += 1
        
        return results
    
    def batch_mark_read(self, message_ids: List[str]) -> Dict[str, int]:
        """
        Mark multiple messages as read in batch.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            Dict with 'success' and 'failed' counts
        """
        return self.batch_modify_messages(message_ids, remove_labels=['UNREAD'])
