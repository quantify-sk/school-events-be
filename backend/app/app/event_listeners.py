from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from app.data_adapter.log import Log
from app.database import Base, SessionLocal
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

# Flag to ensure event listeners are registered only once
_event_listeners_registered = False


def serialize_data(data):
    """Helper function to serialize data for logging."""

    def serialize_value(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [serialize_value(v) for v in value]
        return value

    return {key: serialize_value(value) for key, value in data.items()}


def queue_log_event(
    session: Session,
    table: str,
    table_primary_key: int,
    old_data: dict | None,
    new_data: dict | None,
    user_id: int | None,
) -> None:
    """
    Queue log event to be persisted in the database.

    :param session: SQLAlchemy session to use
    :param table: Table name of the event
    :param table_primary_key: Primary key of the event
    :param old_data: Old data before the event
    :param new_data: New data after the event
    :param user_id: ID of the user who made the change
    """
    # Initialize the log entries if it doesn't exist
    if not hasattr(session, "log_entries"):
        session.log_entries = defaultdict(list)
    # Append the log entry to the list of log entries
    session.log_entries["events"].append(
        (table, table_primary_key, old_data, new_data, user_id)
    )


def commit_log_events(session):
    """
    Commit the log events stored in the session.

    :param session: SQLAlchemy session to use
    """
    # Check if log entries exist in the session
    if hasattr(session, "log_entries"):
        # Iterate over the log events
        for (
            table,
            table_primary_key,
            old_data,
            new_data,
            user_id,
        ) in session.log_entries["events"]:
            # Log each event using a separate session
            log_event(table, table_primary_key, old_data, new_data, user_id)
        # Clear the log entries after committing
        session.log_entries.clear()


def find_diff_keys(old_data: dict, new_data: dict) -> tuple[dict, dict]:
    """
    Find the keys with different values in the old and new dictionaries.

    Args:
        old_data (dict): The original dictionary.
        new_data (dict): The updated dictionary.

    Returns:
        tuple[dict, dict]: A tuple containing two dictionaries. The first dictionary
            contains the keys with different values in the old dictionary, and the
            second dictionary contains the keys with different values in the new
            dictionary.
    """
    # Initialize dictionaries to store the differences
    old_diff = {}
    new_diff = {}

    # Get all keys from both dictionaries
    all_keys = set(old_data.keys()).union(new_data.keys())

    # Iterate over all keys
    for key in all_keys:
        # Get the values for the current key in the old and new dictionaries
        old_value = old_data.get(key)
        new_value = new_data.get(key)

        # Check if the values are different
        if old_value != new_value:
            # Add the key and its value to the corresponding dictionary
            old_diff[key] = old_value
            new_diff[key] = new_value

    # Return the dictionaries containing the differences
    return old_diff, new_diff


def log_event(
    table: str,
    table_primary_key: int,
    old_data: dict | None,
    new_data: dict | None,
    user_id: int | None,
) -> None:
    """
    Logs changes made to a table in the database.

    Args:
        table (str): The name of the table where the change occurred.
        table_primary_key (int): The primary key of the record where the change
            occurred.
        old_data (dict | None): The old data before the change.
        new_data (dict | None): The new data after the change.
        user_id (int | None): The user ID of the user who made the change.
    """
    # Calculate the difference between old and new data
    old_diff, new_diff = {}, {}
    if old_data and new_data:
        # old_diff, new_diff = find_diff_keys(old_data, new_data)
        old_diff, new_diff = old_data, new_data
    elif old_data:
        old_diff = old_data
    elif new_data:
        new_diff = new_data

    # Serialize the old and new data
    serialized_old_data = serialize_data(old_diff) if old_diff else None
    serialized_new_data = serialize_data(new_diff) if new_diff else None

    # Log only if there is a difference
    if serialized_old_data or serialized_new_data:
        with SessionLocal() as log_session:
            log_entry = Log(
                user_id=user_id,
                table_name=table,
                table_primary_key=table_primary_key,
                old_data=serialized_old_data,
                new_data=serialized_new_data,
            )
            log_session.add(log_entry)
            log_session.commit()  # Ensure the log entry is committed


def receive_before_flush(session, flush_context, instances):
    """
    Listener function that runs before a session is flushed.

    It stores the original data of dirty instances in the session's info
    dictionary, so it can be used later to calculate the difference between
    the old and new data.

    Args:
        session (Session): The SQLAlchemy session object.
        flush_context (FlushContext): The SQLAlchemy flush context object.
        instances (List[Base]): The instances that are about to be flushed.
    """
    # Get the custom attributes section of the session's info dictionary
    session_info = session.info.setdefault("custom_attributes", {})

    # Initialize the original data dictionary if it doesn't exist
    if "original_data" not in session_info:
        session_info["original_data"] = {}

    # Loop through the dirty instances in the session
    for instance in session.dirty:
        # Check if the instance is a SQLAlchemy mapped class and not a Log instance
        if isinstance(instance, Base) and not isinstance(instance, Log):
            mapper = inspect(instance).mapper
            primary_key_column = mapper.primary_key[0].name
            primary_key_value = getattr(instance, primary_key_column)

            # Store the original data of the instance in the session's info dictionary
            if primary_key_value not in session_info["original_data"]:
                original_data = {}
                for key in mapper.columns.keys():
                    # Get the history of the instance's attribute
                    history = get_history(instance, key)

                    # If the attribute has changes, store the deleted value as the original data
                    if history.has_changes():
                        original_data[key] = (
                            history.deleted[0] if history.deleted else None
                        )
                    # Otherwise, store the current value as the original data
                    else:
                        original_data[key] = getattr(instance, key)

                # Store the original data of the instance in the session's info dictionary
                session_info["original_data"][primary_key_value] = original_data


def receive_after_flush(session, flush_context):
    """
    Listener function that runs after a session is flushed.

    It handles new instances (creates) and dirty instances (updates)
    by queuing log events for each instance.

    Args:
        session (Session): The SQLAlchemy session object.
        flush_context (FlushContext): The SQLAlchemy flush context object.
    """
    from app.context_manager import context_actor_user_data

    # Get the custom attributes section of the session's info dictionary
    session_info = session.info.setdefault("custom_attributes", {})

    # Initialize the log_entries dictionary if it doesn't exist
    if "log_entries" not in session_info:
        session_info["log_entries"] = defaultdict(list)

    # Handle new instances (creates)
    for instance in session.new:
        # Check if the instance is a SQLAlchemy mapped class and not a Log instance
        if isinstance(instance, Base) and not isinstance(instance, Log):
            mapper = inspect(instance).mapper
            primary_key_column = mapper.primary_key[0].name
            primary_key_value = getattr(instance, primary_key_column)
            new_data = {}
            for key in mapper.columns.keys():
                new_data[key] = getattr(instance, key)

            user_id = (
                context_actor_user_data.get().user_id
                if context_actor_user_data.get()
                else None
            )
            queue_log_event(
                session,
                instance.__tablename__,
                primary_key_value,
                None,  # No old data for creates
                new_data,
                user_id,
            )

    # Handle dirty instances (updates)
    for instance in session.dirty:
        # Check if the instance is a SQLAlchemy mapped class and not a Log instance
        if isinstance(instance, Base) and not isinstance(instance, Log):
            mapper = inspect(instance).mapper
            primary_key_column = mapper.primary_key[0].name
            primary_key_value = getattr(instance, primary_key_column)
            old_data = session_info["original_data"].get(primary_key_value, {})
            new_data = {}
            for key in mapper.columns.keys():
                new_data[key] = getattr(instance, key)

            user_id = (
                context_actor_user_data.get().user_id
                if context_actor_user_data.get()
                else None
            )
            queue_log_event(
                session,
                instance.__tablename__,
                primary_key_value,
                old_data,
                new_data,
                user_id,
            )

    # Clear the original data after flushing
    session_info["original_data"].clear()


def receive_after_commit(session):
    """
    Listener function that runs after a session is committed.

    It commits the log events stored in the session.

    Args:
        session (Session): The SQLAlchemy session object.
    """
    # Commit the log events stored in the session
    commit_log_events(session)


def receive_persistent_to_deleted(session, instance):
    """
    Listener function that runs when a persistent instance is deleted.

    It queues a log event for the deleted instance.

    Args:
        session (Session): The SQLAlchemy session object.
        instance (Base): The instance being deleted.
    """
    # Import the context actor user data module
    from app.context_manager import context_actor_user_data

    # Check if the instance is a SQLAlchemy mapped class and not a Log instance
    if isinstance(instance, Base) and not isinstance(instance, Log):
        # Get the mapper for the instance
        mapper = inspect(instance).mapper
        # Get the old data for the instance
        old_data = {key: getattr(instance, key) for key in mapper.columns.keys()}
        # Get the primary key column and value for the instance
        primary_key_column = mapper.primary_key[0].name
        primary_key_value = getattr(instance, primary_key_column)
        # Get the user ID from the context actor user data module
        user_id = (
            context_actor_user_data.get().user_id
            if context_actor_user_data.get()
            else None
        )
        # Queue a log event for the deleted instance
        queue_log_event(
            session,
            instance.__tablename__,
            primary_key_value,
            old_data,
            None,
            user_id,
        )


def register_event_listeners():
    """
    Register event listeners for the SQLAlchemy session.

    This function registers event listeners for the SQLAlchemy session object.
    The registered event listeners are:
    - before_flush: Runs before the session is flushed.
    - after_flush: Runs after the session is flushed.
    - after_commit: Runs after the session is committed.
    - persistent_to_deleted: Runs when a persistent instance is deleted.
    """
    global _event_listeners_registered
    # Check if the event listeners are already registered
    if not _event_listeners_registered:
        # Register the event listeners
        event.listen(Session, "before_flush", receive_before_flush)
        # Register the event listener for after the session is flushed
        event.listen(Session, "after_flush", receive_after_flush)
        # Register the event listener for after the session is committed
        event.listen(Session, "after_commit", receive_after_commit)
        # Register the event listener for when a persistent instance is deleted
        event.listen(Session, "persistent_to_deleted", receive_persistent_to_deleted)
        # Set the flag to indicate that the event listeners are registered
        _event_listeners_registered = True
