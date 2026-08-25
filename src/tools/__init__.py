from .datetime_tool import get_current_datetime
from .web_search import web_search
from .file_operations import read_file, write_file, list_files
from .todo_manager import manage_todo
from .flashcards import manage_flashcards
from .quiz import generate_quiz
from .summarizer import summarize_text
from .code_runner import run_code
from .performance_tracker import (
    track_study_session,
    record_quiz_result,
    record_flashcard_review_result,
    get_performance_report,
)
from .adaptive_recommender import (
    get_study_recommendation,
    get_method_rankings,
    get_bandit_insights,
)
from .always_on_tools import (
    # Always-on mode
    set_always_on,
    get_always_on_status,
    set_reminder_interval,
    set_quiet_hours,
    set_preferred_name,
    # Voice & security
    enable_voice_lock,
    manage_voice,
    set_pin_code,
    create_access_session,
    # Learning profile
    get_learning_profile,
    update_learning_profile,
    # Career & growth
    manage_skill,
    manage_milestone,
    manage_academic_goal,
    manage_career_goal,
    get_growth_report,
    earn_xp,
)

# Every tool the agent can call. Add new tools here as you build them —
# the graph in agent.py picks up whatever's in this list automatically.
TOOLS = [
    # Core tools
    web_search,
    get_current_datetime,
    # File operations
    read_file,
    write_file,
    list_files,
    # Productivity
    manage_todo,
    # Study tools
    manage_flashcards,
    generate_quiz,
    summarize_text,
    # Code tools
    run_code,
    # Performance tracking & adaptive learning
    track_study_session,
    record_quiz_result,
    record_flashcard_review_result,
    get_performance_report,
    get_study_recommendation,
    get_method_rankings,
    get_bandit_insights,
    # Always-on mode & proactive reminders
    set_always_on,
    get_always_on_status,
    set_reminder_interval,
    set_quiet_hours,
    set_preferred_name,
    # Voice lock & security
    enable_voice_lock,
    manage_voice,
    set_pin_code,
    create_access_session,
    # Learning style profiling
    get_learning_profile,
    update_learning_profile,
    # Career & academic growth
    manage_skill,
    manage_milestone,
    manage_academic_goal,
    manage_career_goal,
    get_growth_report,
    earn_xp,
]
