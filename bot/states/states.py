from aiogram.fsm.state import State, StatesGroup


class AddHomework(StatesGroup):
    choose_subject = State()
    topics_count = State()
    description = State()
    attachment = State()
    confirm = State()


class ManageAdmins(StatesGroup):
    waiting_for_user = State()
