"""Secure credential management for APIs and services."""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


LOGGER = logging.getLogger(__name__)


class CredentialType(Enum):
    """Types of credentials that can be stored."""
    API_KEY = "api_key"
    USERNAME_PASSWORD = "username_password"
    TOKEN = "token"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"


@dataclass
class Credential:
    """Represents a single credential."""
    id: str
    name: str
    type: CredentialType
    value: str
    service: str
    created_at: float
    expires_at: Optional[float] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class CredentialStore(ABC):
    """Abstract base class for credential storage."""
    
    @abstractmethod
    def store_credential(self, credential: Credential) -> bool:
        """Store a credential."""
        pass
    
    @abstractmethod
    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID."""
        pass
    
    @abstractmethod
    def list_credentials(self, service: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Credential]:
        """List credentials, optionally filtered by service or tags."""
        pass
    
    @abstractmethod
    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential by ID."""
        pass
    
    @abstractmethod
    def update_credential(self, credential: Credential) -> bool:
        """Update an existing credential."""
        pass


class InMemoryCredentialStore(CredentialStore):
    """In-memory implementation of credential store."""
    
    def __init__(self) -> None:
        self._credentials: Dict[str, Credential] = {}
    
    def store_credential(self, credential: Credential) -> bool:
        """Store a credential in memory."""
        self._credentials[credential.id] = credential
        return True
    
    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID from memory."""
        return self._credentials.get(credential_id)
    
    def list_credentials(self, service: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Credential]:
        """List credentials, optionally filtered by service or tags."""
        credentials = list(self._credentials.values())
        
        if service:
            credentials = [cred for cred in credentials if cred.service == service]
        
        if tags:
            credentials = [
                cred for cred in credentials
                if any(tag in cred.tags for tag in tags)
            ]
        
        return credentials
    
    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential by ID from memory."""
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            return True
        return False
    
    def update_credential(self, credential: Credential) -> bool:
        """Update an existing credential in memory."""
        if credential.id in self._credentials:
            self._credentials[credential.id] = credential
            return True
        return False


class EncryptedFileCredentialStore(CredentialStore):
    """Encrypted file-based implementation of credential store."""
    
    def __init__(self, storage_path: Path, encryption_key: Optional[bytes] = None) -> None:
        self._storage_path = storage_path
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._credentials_file = self._storage_path / "credentials.json"
        
        # Generate or load encryption key
        if encryption_key is None:
            # Try to load from environment or generate new one
            key_env = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
            if key_env:
                self._encryption_key = key_env.encode()
            else:
                self._encryption_key = Fernet.generate_key()
                # In a real implementation, we'd want to securely store this key
                # For now, we'll log a warning about this
                LOGGER.warning("Generated new encryption key. In production, securely store this key.")
        else:
            self._encryption_key = encryption_key
        
        self._cipher_suite = Fernet(self._encryption_key)
        self._credentials: Dict[str, Credential] = {}
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load credentials from encrypted file."""
        if self._credentials_file.exists():
            try:
                encrypted_data = self._credentials_file.read_bytes()
                decrypted_data = self._cipher_suite.decrypt(encrypted_data)
                credentials_dict = json.loads(decrypted_data.decode())
                
                # Convert dict back to Credential objects
                for cred_id, cred_data in credentials_dict.items():
                    credential = Credential(
                        id=cred_data['id'],
                        name=cred_data['name'],
                        type=CredentialType(cred_data['type']),
                        value=cred_data['value'],
                        service=cred_data['service'],
                        created_at=cred_data['created_at'],
                        expires_at=cred_data.get('expires_at'),
                        tags=cred_data.get('tags', [])
                    )
                    self._credentials[cred_id] = credential
            except Exception as e:
                LOGGER.error(f"Failed to load credentials from file: {e}")
    
    def _save_credentials(self) -> None:
        """Save credentials to encrypted file."""
        try:
            # Convert credentials to dict
            credentials_dict = {}
            for cred_id, credential in self._credentials.items():
                credentials_dict[cred_id] = {
                    'id': credential.id,
                    'name': credential.name,
                    'type': credential.type.value,
                    'value': credential.value,
                    'service': credential.service,
                    'created_at': credential.created_at,
                    'expires_at': credential.expires_at,
                    'tags': credential.tags
                }
            
            # Serialize and encrypt
            json_data = json.dumps(credentials_dict).encode()
            encrypted_data = self._cipher_suite.encrypt(json_data)
            self._credentials_file.write_bytes(encrypted_data)
        except Exception as e:
            LOGGER.error(f"Failed to save credentials to file: {e}")
    
    def store_credential(self, credential: Credential) -> bool:
        """Store a credential to encrypted file."""
        self._credentials[credential.id] = credential
        self._save_credentials()
        return True
    
    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID from encrypted file."""
        # Refresh from file to ensure latest data
        self._load_credentials()
        return self._credentials.get(credential_id)
    
    def list_credentials(self, service: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Credential]:
        """List credentials from encrypted file, optionally filtered."""
        # Refresh from file to ensure latest data
        self._load_credentials()
        
        credentials = list(self._credentials.values())
        
        if service:
            credentials = [cred for cred in credentials if cred.service == service]
        
        if tags:
            credentials = [
                cred for cred in credentials
                if any(tag in cred.tags for tag in tags)
            ]
        
        return credentials
    
    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential by ID from encrypted file."""
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            self._save_credentials()
            return True
        return False
    
    def update_credential(self, credential: Credential) -> bool:
        """Update an existing credential in encrypted file."""
        if credential.id in self._credentials:
            self._credentials[credential.id] = credential
            self._save_credentials()
            return True
        return False


class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def __init__(self, credential_store: CredentialStore) -> None:
        self._credential_store = credential_store
    
    def store_credential(
        self,
        name: str,
        credential_type: CredentialType,
        value: str,
        service: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a new credential and return its ID."""
        import time
        credential_id = f"cred_{int(time.time() * 1000)}_{hash(name) % 10000}"
        
        credential = Credential(
            id=credential_id,
            name=name,
            type=credential_type,
            value=value,
            service=service,
            created_at=time.time(),
            tags=tags or []
        )
        
        success = self._credential_store.store_credential(credential)
        if success:
            LOGGER.info(f"Stored credential: {credential_id} for {service}")
            return credential_id
        else:
            raise Exception(f"Failed to store credential for {service}")
    
    def get_credential_value(self, credential_id: str) -> Optional[str]:
        """Get the value of a credential by ID."""
        credential = self._credential_store.get_credential(credential_id)
        if credential:
            # Check if credential has expired
            if credential.expires_at and credential.expires_at < time.time():
                LOGGER.warning(f"Credential {credential_id} has expired")
                self._credential_store.delete_credential(credential_id)
                return None
            return credential.value
        return None
    
    def get_credential_by_name_and_service(self, name: str, service: str) -> Optional[Credential]:
        """Get a credential by name and service."""
        credentials = self._credential_store.list_credentials(service=service)
        for credential in credentials:
            if credential.name == name:
                # Check if credential has expired
                if credential.expires_at and credential.expires_at < time.time():
                    LOGGER.warning(f"Credential {credential.id} has expired")
                    self._credential_store.delete_credential(credential.id)
                    continue
                return credential
        return None
    
    def list_credentials(self, service: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Credential]:
        """List credentials, optionally filtered by service or tags."""
        return self._credential_store.list_credentials(service=service, tags=tags)
    
    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential by ID."""
        success = self._credential_store.delete_credential(credential_id)
        if success:
            LOGGER.info(f"Deleted credential: {credential_id}")
        return success
    
    def update_credential(self, credential: Credential) -> bool:
        """Update an existing credential."""
        return self._credential_store.update_credential(credential)
    
    def rotate_credential(self, credential_id: str, new_value: str) -> bool:
        """Rotate the value of an existing credential."""
        credential = self._credential_store.get_credential(credential_id)
        if not credential:
            return False
        
        import time
        credential.value = new_value
        credential.created_at = time.time()
        
        return self._credential_store.update_credential(credential)