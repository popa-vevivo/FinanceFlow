"""Application-specific exceptions.

Every error carries a message that is safe to show to the user as is.
"""


class FinanceFlowError(Exception):
    """Base class for all expected application errors."""


class ValidationError(FinanceFlowError):
    """User input or a domain rule is invalid."""


class RepositoryError(FinanceFlowError):
    """The storage layer failed to complete an operation."""


class NotFoundError(RepositoryError):
    """The requested record does not exist."""
