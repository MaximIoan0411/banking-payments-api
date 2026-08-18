import enum


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    PAYMENT = "payment"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"