from enum import Enum


class TransactionType(Enum):
    BUY = "buy"
    SELL = "sell"

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def from_str(label: str):
        """
        Method to create an `OrderType` enum from the following qualifying strings:
        'b', 'buy' => OrderType.BUY
        's', 'sell' => OrderType.SELL

        """
        label = label.lower()
        if label in ("b", "buy"):
            label = TransactionType.BUY
        elif label in ("s", "sell"):
            label = TransactionType.SELL
        else:
            raise TypeError("Unrecognized `OrderType` enum.")

        return label


class OrderingStrategy(Enum):
    FIFO = "first-in first-out"
    LIFO = "last-in first-out"

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def from_str(label: str):
        """
        Method to create an `OrderType` enum from the following qualifying strings:
        'fifo' => OrderingStrategy.FIFO
        'lifo' => OrderingStrategy.LIFO

        """
        label = label.lower()
        if label in ("fifo"):
            label = OrderingStrategy.FIFO
        elif label in ("lifo"):
            label = OrderingStrategy.LIFO
        else:
            raise TypeError("Unrecognized `OrderingStrategy` enum.")

        return label
