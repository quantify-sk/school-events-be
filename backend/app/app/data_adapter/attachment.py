import base64
import json
import os
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.context_manager import get_db_session


class Attachment(Base):
    """
    Represents an attachment in the system.

    This class defines the structure and behavior of attachment objects, including
    database schema, initialization, and various operations like creation and retrieval.
    """

    __tablename__ = "attachment"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Attachment information
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)

    event_id = Column(Integer, ForeignKey("event.id"))

    # Use string reference for late-binding
    event = relationship("Event", back_populates="attachments")

    def __init__(
        self,
        name: str,
        path: str,
        type: str,
        event_id: int = None,
        event: "Event" = None,  # Add this line
    ):
        self.name = name
        self.path = path
        self.type = type
        if event:  # Add this block
            self.event = event
        else:
            self.event_id = event_id

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the Attachment instance to a dictionary representation,
        including base64 encoded file content.

        Returns:
            Dict[str, Any]: A dictionary containing all attachment attributes and file data.
        """
        model = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "event_id": self.event_id,
        }

        # Add base64 encoded file content
        if os.path.exists(self.path):
            with open(self.path, "rb") as file:
                file_data = file.read()
                base64_data = base64.b64encode(file_data).decode("utf-8")
                model["data"] = base64_data
        else:
            model["data"] = None

        return model

    @classmethod
    def create_new_attachment(cls, attachment_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a new attachment in the database.

        Args:
            attachment_data (Dict[str, str]): The data for the new attachment.

        Returns:
            Dict[str, Any]: The created attachment as a dictionary.
        """
        db = get_db_session()
        new_attachment = cls(
            **attachment_data,
        )
        db.add(new_attachment)
        db.commit()
        db.refresh(new_attachment)
        return new_attachment._to_model()

    @classmethod
    def get_attachment_by_id(cls, attachment_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve an attachment by its ID.

        Args:
            attachment_id (int): The ID of the attachment to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The attachment as a dictionary if found, None otherwise.
        """
        db = get_db_session()
        attachment = db.query(cls).filter(cls.id == attachment_id).first()
        return attachment._to_model() if attachment else None

    @classmethod
    def update_attachment_by_id(
        cls,
        attachment_id: int,
        attachment_data: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing attachment by ID.

        Args:
            attachment_id (int): The ID of the attachment to update.
            attachment_data (Dict[str, str]): The updated attachment data.

        Returns:
            Optional[Dict[str, Any]]: The updated attachment as a dictionary, or None if the attachment was not found.
        """
        db = get_db_session()
        attachment = db.query(cls).filter(cls.id == attachment_id).first()
        if attachment:
            for field, value in attachment_data.items():
                setattr(attachment, field, value)
            db.commit()
            db.refresh(attachment)
            return attachment._to_model()
        return None

    @classmethod
    def delete_attachment_by_id(cls, attachment_id: int) -> bool:
        """
        Delete an attachment by its ID.

        Args:
            attachment_id (int): The ID of the attachment to delete.

        Returns:
            bool: True if the attachment was successfully deleted, False otherwise.
        """
        db = get_db_session()
        attachment = db.query(cls).filter(cls.id == attachment_id).first()
        if attachment:
            db.delete(attachment)
            db.commit()
            return True
        return False
