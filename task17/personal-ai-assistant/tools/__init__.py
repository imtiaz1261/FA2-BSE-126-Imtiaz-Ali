"""
tools package
-------------
Central registry: every tool the agent can call is imported and
listed here, so agent.py just does `from tools import ALL_TOOLS`.
"""

from tools.calculator_tool import calculator
from tools.weather_tool import weather
from tools.search_tool import web_search
from tools.file_tool import read_file
from tools.notes_tool import save_note, list_notes, delete_note
from tools.reminder_tool import create_reminder, list_reminders, delete_reminder

ALL_TOOLS = [
    calculator,
    weather,
    web_search,
    read_file,
    save_note,
    list_notes,
    delete_note,
    create_reminder,
    list_reminders,
    delete_reminder,
]
