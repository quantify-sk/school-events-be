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

    ERR_EVENT_NOT_FOUND = "Event not found"
    ERR_CREATE_EVENT = "Error creating event"

    ERR_RESERVATION_NOT_FOUND = "Reservation not found"
    ERR_INSUFFICIENT_CAPACITY = "Insufficient capacity for the reservation"
    ERR_INVALID_RESERVATION_DATA = "Invalid reservation data"
    ERR_INVALID_NUMBER_OF_SEATS = (
        "Invalid number of seats. The number of seats must be greater than zero."
    )
    MSG_SUCCESS_GET_RESERVATIONS_BY_EVENT = "Reservations retrieved successfully"

    # School messages
    ERR_MISSING_SCHOOL_DATA = "Missing school data"
    SCHOOL_CREATION_FAILED = "School creation failed"
