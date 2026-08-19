import enum


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    PAYMENT = "payment"
    TRANSFER_IN = "transfer_in"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"