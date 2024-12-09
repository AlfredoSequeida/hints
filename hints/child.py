"""Child to represent an application's element."""


class Child:
    def __init__(
        self,
        absolute_position: tuple[float, float],
        relative_position: tuple[float, float],
    ):
        self.absolute_position = absolute_position
        self.relative_position = relative_position
