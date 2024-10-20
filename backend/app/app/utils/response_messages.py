class ResponseMessages:
    # Success messages
    MSG_SUCCESS_LOGIN = "Login successful"
    MSG_SUCCESS_LOGOUT = "Logout successful"
    MSG_SUCCESS_ADD_LABORANT = "Successfully added laborant"
    MSG_SUCCESS_REMOVE_LABORANT = "Successfully removed laborant"
    MSG_SUCCESS_CREATE_USER = "User created successfully"
    MSG_SUCCESS_GET_USER_PROJECTS = "User projects retrieved successfully"
    MSG_SUCCESS_GET_ALL_USERS = "All users retrieved successfully"
    MSG_SUCCESS_UPDATE_USER = "User updated successfully"
    MSG_SUCCESS_GET_USER = "User retrieved successfully"
    MSG_SUCCESS_DELETE_USER = "User deleted successfully"
    MSG_SUCCESS_GET_USER_ROLE = "User role retrieved successfully"
    ERR_ACCOUNT_PENDING_APPROVAL = "Account pending approval"

    MSG_SUCCESS_CREATE_EVENT = "Event created successfully"
    MSG_SUCCESS_UPDATE_EVENT = "Event updated successfully"
    MSG_SUCCESS_DELETE_EVENT = "Event deleted successfully"
    MSG_SUCCESS_GET_EVENT = "Event retrieved successfully"
    MSG_SUCCESS_GET_ALL_EVENTS = "All events retrieved successfully"
    MSG_SUCCESS_GET_ORGANIZER_EVENTS = "Organizer events retrieved successfully"
    MSG_SUCCESS_GET_PENDING_USERS = "Pending users retrieved successfully"
    MSG_SUCCESS_APPROVE_USER = "User approved successfully"
    MSG_SUCCESS_REJECT_USER = "User rejected successfully"

    MSG_SUCCESS_CREATE_RESERVATION = "Reservation created successfully"
    MSG_SUCCESS_UPDATE_RESERVATION = "Reservation updated successfully"
    MSG_SUCCESS_DELETE_RESERVATION = "Reservation deleted successfully"
    MSG_SUCCESS_GET_RESERVATION = "Reservation retrieved successfully"
    MSG_SUCCESS_GET_ALL_RESERVATIONS = "All reservations retrieved successfully"
    MSG_SUCCESS_GET_USER_RESERVATIONS = "User reservations retrieved successfully"
    MSG_SUCCESS_GET_USER_EVENT_RESERVATIONS = (
        "User event reservations retrieved successfully"
    )
    MSG_SUCCESS_GET_PARENT_ORGANIZER = "Parent organizer retrieved successfully"
    MSG_SUCCESS_MARK_PAID = "Reservation marked as paid successfully"
    MSG_SUCCESS_MARK_COMPLETED = "Reservation marked as completed successfully"

    # Error messages
    ERR_USER_NOT_FOUND = "User not found"
    ERR_LABORANT_NOT_ASSIGNED_TO_USER = "Laborant not assigned to user"
    ERR_USER_ALREADY_EXISTS = "User already exists"
    ERR_EMAIL_ALREADY_TAKEN = "Email already taken"
    ERR_ROUTE_NOT_FOUND = "Route not found"
    ERR_INVALID_USER_CREDENTIALS = "Invalid user credentials"
    ERR_INVALID_REFRESH_TOKEN = "Invalid refresh token"
    ERR_USER_NOT_LOGGED_IN = "User not logged in"
    ERR_TOKEN_EXPIRED = "Token expired"
    ERR_TOKEN_INVALID = "Token invalid"
    ERR_TOKEN_NOT_PROVIDED = "Token not provided"
    ERR_INVALID_DATA = "Invalid data"
    ERR_INVALID_USER_ID = "Invalid user ID"
    ERR_MARK_PAID = "Error marking reservation as paid"
    ERR_MARK_COMPLETED = "Error marking reservation as completed"

    ERR_EVENT_NOT_FOUND = "Event not found"
    ERR_CREATE_EVENT = "Error creating event"
    ERR_INVALID_EVENT_DATE_DATA = "Invalid event date data"

    ERR_RESERVATION_NOT_FOUND = "Reservation not found"
    ERR_INSUFFICIENT_CAPACITY = "Insufficient capacity for the reservation"
    ERR_INVALID_RESERVATION_DATA = "Invalid reservation data"
    ERR_INVALID_NUMBER_OF_SEATS = (
        "Invalid number of seats. The number of seats must be greater than zero."
    )
    MSG_SUCCESS_FIND_RESERVATION = "Reservation found"
    MSG_NO_PARENT_ORGANIZER_FOUND = "No parent organizer found"
    ERR_RESERVATION_ALREADY_CANCELLED = "Reservation already cancelled"
    ERR_UPDATE_EVENT = "Error updating event"
    MSG_SUCCESS_GET_RESERVATIONS_BY_EVENT = "Reservations retrieved successfully"
    MSG_SUCCESS_CONFIRM_RESERVATION = "Reservation confirmed successfully"
    ERR_EVENT_DATE_NOT_FOUND = (
        "The specified event date was not found or does not belong to the event."
    )
    MSG_SUCCESS_GET_EVENT_DATE = "Event date retrieved successfully"

    # School messages
    ERR_MISSING_SCHOOL_DATA = "Missing school data"
    ERR_SCHOOL_ALREADY_REGISTERED = "School already registered"
    SCHOOL_CREATION_FAILED = "School creation failed"

    ERR_INTERNAL_SERVER_ERROR = "Internal server error"

    MSG_SUCCESS_GET_ORGANIZERS = "Organizers retrieved successfully"

    # Waiting list messages
    MSG_SUCCESS_ADD_TO_WAITING_LIST = "Added to waiting list successfully"
    MSG_SUCCESS_PROCESS_WAITING_LIST = "Processed waiting list successfully"
    MSG_SUCCESS_GET_USER_WAITING_LIST = (
        "User waiting list entries retrieved successfully"
    )
    MSG_SUCCESS_UPDATE_WAITING_LIST_ENTRY = "Waiting list entry updated successfully"
    MSG_SUCCESS_DELETE_WAITING_LIST_ENTRY = "Waiting list entry deleted successfully"
    MSG_SUCCESS_GET_WAITING_LIST_ENTRIES = "Waiting list entries retrieved successfully"
    MSG_SUCCESS_GET_WAITING_LIST = "Waiting list retrieved successfully"
    MSG_SUCCESS_GET_WAITING_LIST_ENTRY = "Waiting list entry retrieved successfully"

    ERR_INVALID_WAITING_LIST_DATA = "Invalid waiting list data"
    ERR_EVENT_DATE_LOCKED = "Event date is locked"
    MSG_NO_WAITING_LIST_ENTRIES = "No waiting list entries found"
    ERR_WAITING_LIST_ENTRY_NOT_FOUND = "Waiting list entry not found"

    # Report messages
    MSG_SUCCESS_GENERATE_REPORT = "Report generated successfully"
    MSG_SUCCESS_GET_ALL_REPORTS = "All reports retrieved successfully"
    MSG_SUCCESS_GET_REPORT = "Report retrieved successfully"
    MSG_SUCCESS_EXPORT_REPORT = "Report exported successfully"
    MSG_SUCCESS_SAVE_REPORT = "Report saved successfully"
    MSG_SUCCESS_DELETE_REPORT = "Report deleted successfully"

    ERR_REPORT_NOT_FOUND = "Report not found"
    ERR_INVALID_REPORT_INPUT = "Invalid input for report generation"

    # Event claims
    MSG_SUCCESS_CREATE_CLAIM = "Claim created successfully"
    MSG_SUCCESS_GET_PENDING_CLAIMS = "Pending claims retrieved successfully"

    ERR_GET_PENDING_CLAIMS = "Error getting pending claims"
    ERR_CREATE_CLAIM = "Error creating claim"
    ERR_CLAIM_NOT_FOUND = "Claim not found"
    ERR_UPDATE_CLAIM = "Error updating claim"
    MSG_SUCCESS_UPDATE_CLAIM = "Claim updated successfully"

    MSG_SUCCESS_GET_STATISTICS = "Statistics retrieved successfully"
    ERR_GENERATING_STATISTICS = "Error generating statistics"

    MSG_SUCCESS_GET_ALL_EVENTS_WITH_DATES = (
        "All events with dates retrieved successfully"
    )
