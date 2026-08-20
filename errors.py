class DomainError(Exception):
    """Base domain exception."""


class SourceRequiredError(DomainError):
    pass


class InsufficientEvidenceError(DomainError):
    pass


class CurrencyConflictError(DomainError):
    pass


class DuplicateEconomicEventError(DomainError):
    pass
