"""Registration flow FSM states."""

from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """States for the registration flow.

    Flow: start -> consent -> test_q1 -> test_q2 -> test_q3 -> test_q4 -> complete
    """

    start = State()
    consent = State()
    test_q1 = State()
    test_q2 = State()
    test_q3 = State()
    test_q4 = State()
    complete = State()
