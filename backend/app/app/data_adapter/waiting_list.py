import app.logger
from datetime import datetime
import fastapi
from typing import Any, Dict, List, Optional, Tuple, Union
from app.database import Base
from app.models.waiting_list import WaitingListStatus
from app.logger import logger
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.context_manager import get_db_session
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    ForeignKey,
    func,
    asc,
    desc,
    Boolean,
)


class WaitingList(Base):
    __tablename__ = "waiting_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date_id = Column(Integer, ForeignKey("event_date.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    number_of_students = Column(Integer, nullable=False)
    number_of_teachers = Column(Integer, nullable=False)
    special_requirements = Column(String(255), nullable=True)
    contact_info = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(SAEnum(WaitingListStatus), default=WaitingListStatus.WAITING)
    position = Column(Integer, nullable=False)  # Add this line

    event_date = relationship("EventDate", back_populates="waiting_list")
    user = relationship("User", back_populates="waiting_list")
    event = relationship("Event", back_populates="waiting_list")

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_date_id": self.event_date_id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "number_of_students": self.number_of_students,
            "number_of_teachers": self.number_of_teachers,
            "special_requirements": self.special_requirements,
            "contact_info": self.contact_info,
            "created_at": self.created_at,
            "status": self.status,
            "position": self.position,  # Add this line
        }

    @classmethod
    def add_to_waiting_list(
        cls, waiting_list_entry: Dict[str, Any]
    ) -> Optional["WaitingList"]:
        try:
            with get_db_session() as db:
                # Get the current highest position for this event date
                highest_position = (
                    db.query(func.max(cls.position))
                    .filter(
                        cls.event_date_id == waiting_list_entry["event_date_id"],
                        cls.status == WaitingListStatus.WAITING,
                    )
                    .scalar()
                    or 0
                )

                # Assign the next position
                waiting_list_entry["position"] = highest_position + 1

                new_entry = cls(**waiting_list_entry)
                db.add(new_entry)
                db.commit()
                db.refresh(new_entry)
                return new_entry
        except Exception as e:
            print(f"Error adding to waiting list: {str(e)}")
            raise

    @classmethod
    def update_status(
        cls, entry_id: int, new_status: WaitingListStatus
    ) -> Optional["WaitingList"]:
        try:
            with get_db_session() as db:
                entry = db.query(cls).filter(cls.id == entry_id).first()
                if entry:
                    old_status = entry.status
                    entry.status = new_status
                    db.commit()
                    db.refresh(entry)

                    if (
                        old_status == WaitingListStatus.WAITING
                        or new_status == WaitingListStatus.WAITING
                    ):
                        cls.reorder_positions(entry.event_date_id)

                return entry
        except Exception as e:
            print(f"Error updating waiting list entry status: {str(e)}")
            raise

    @classmethod
    def get_user_waiting_list_entries(cls, user_id: int) -> List["WaitingList"]:
        try:
            with get_db_session() as db:
                return db.query(cls).filter(cls.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error retrieving user waiting list entries: {str(e)}")
            raise

    @classmethod
    def delete_waiting_list_entry(cls, waiting_list_id: int) -> bool:
        try:
            with get_db_session() as db:
                entry = db.query(cls).filter(cls.id == waiting_list_id).first()
                if entry:
                    event_date_id = entry.event_date_id
                    position = entry.position
                    db.delete(entry)

                    # Reorder positions for remaining entries
                    remaining_entries = (
                        db.query(cls)
                        .filter(
                            cls.event_date_id == event_date_id,
                            cls.position > position,
                            cls.status == WaitingListStatus.WAITING,
                        )
                        .order_by(cls.position)
                        .all()
                    )

                    for remaining_entry in remaining_entries:
                        remaining_entry.position -= 1

                    db.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting waiting list entry: {str(e)}")
            raise

    @classmethod
    def reorder_positions(cls, event_date_id: int):
        try:
            with get_db_session() as db:
                entries = (
                    db.query(cls)
                    .filter(
                        cls.event_date_id == event_date_id,
                        cls.status == WaitingListStatus.WAITING,
                    )
                    .order_by(cls.position)
                    .all()
                )

                for i, entry in enumerate(entries, start=1):
                    entry.position = i

                db.commit()
        except Exception as e:
            print(f"Error reordering waiting list positions: {str(e)}")
            raise

    @classmethod
    def get_waiting_list_for_event_date(
        cls,
        event_date_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List["WaitingList"], int]:
        """
        Retrieve the waiting list for a specific event date with pagination, filtering, and sorting.

        Args:
            event_date_id (int): The ID of the event date.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            Tuple[List['WaitingList'], int]: A tuple containing the list of WaitingList objects and the total count.
        """
        try:
            with get_db_session() as db:
                query = db.query(cls).filter(
                    cls.event_date_id == event_date_id,
                    cls.status == WaitingListStatus.WAITING,
                )

                # Apply filters
                if filter_params:
                    for key, value in filter_params.items():
                        if hasattr(cls, key):
                            if isinstance(value, list):
                                query = query.filter(getattr(cls, key).in_(value))
                            else:
                                query = query.filter(getattr(cls, key) == value)

                # Apply sorting
                if sorting_params:
                    for sort_param in sorting_params:
                        for key, direction in sort_param.items():
                            if hasattr(cls, key):
                                if direction.lower() == "desc":
                                    query = query.order_by(desc(getattr(cls, key)))
                                else:
                                    query = query.order_by(asc(getattr(cls, key)))

                # Get total count
                total_count = query.count()

                # Apply pagination
                query = query.offset((current_page - 1) * items_per_page).limit(
                    items_per_page
                )

                # Execute query
                waiting_list_entries = query.all()

                return waiting_list_entries, total_count

        except Exception as e:
            logger.error(
                f"Error retrieving waiting list for event date {event_date_id}: {str(e)}"
            )
            raise

    @classmethod
    def get_by_event_date_and_user(
        cls, event_date_id: int, user_id: int
    ) -> Optional["WaitingList"]:
        try:
            with get_db_session() as db:
                return (
                    db.query(cls)
                    .filter(cls.event_date_id == event_date_id, cls.user_id == user_id)
                    .first()
                )
        except Exception as e:
            logger.error(
                f"Error retrieving waiting list entry by event date and user: {str(e)}"
            )
            raise

    @classmethod
    def get_by_id(cls, waiting_list_id: int) -> Optional["WaitingList"]:
        try:
            print("WaitingList.get_by_id", waiting_list_id)
            with get_db_session() as db:
                return db.query(cls).filter(cls.id == waiting_list_id).first()
        except Exception as e:
            logger.error(f"Error retrieving waiting list entry by ID: {str(e)}")
            raise
