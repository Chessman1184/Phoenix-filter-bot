import os
import glob

def clean_old_sessions():
    """Clean old session files"""
    session_dir = "sessions"
    if not os.path.exists(session_dir):
        return
        
    # Keep only the latest 3 session files
    sessions = glob.glob(os.path.join(session_dir, "phoenix-filter-bot*"))
    if len(sessions) > 3:
        sessions.sort(key=os.path.getctime)
        for old_session in sessions[:-3]:
            try:
                os.remove(old_session)
            except:
                pass

if __name__ == "__main__":
    clean_old_sessions()
