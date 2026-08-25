"""
Security module — voice lock, PIN access, and authorized voice management.

The agent should only respond to authorized voices. This module handles:
  - Voice fingerprint registration (via audio feature hash)
  - Voice lock verification
  - PIN code backup access
  - Session token management
"""

import hashlib
import json
import secrets
import time
from datetime import datetime
from pathlib import Path

from .scheduler import get_settings, update_settings

SECURITY_FILE = Path("nova_security.json")

# Active sessions (session_token -> {user_id, created_at, expires_at})
_sessions: dict[str, dict] = {}
SESSION_TTL = 3600 * 8  # 8 hours


def _load_security() -> dict:
    if SECURITY_FILE.exists():
        try:
            return json.loads(SECURITY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "voice_lock_enabled": False,
        "voice_passphrase": "",
        "voice_fingerprints": [],  # list of {"hash": ..., "label": ..., "added": ...}
        "pin_code": "",
        "max_attempts": 5,
        "lockout_until": None,
    }


def _save_security(data: dict):
    SECURITY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Voice Fingerprint Management ────────────────────────────────

def hash_voice_fingerprint(audio_features: str) -> str:
    """
    Create a stable hash from voice audio features.
    
    In the browser, the Web Speech API provides transcript confidence 
    and timing data. We hash a combination of those to create a 
    lightweight 'voice fingerprint' that differentiates speakers.
    
    For production, you'd use a proper speaker verification model.
    """
    return hashlib.sha256(audio_features.encode()).hexdigest()[:32]


def register_voice(label: str, audio_features: str) -> str:
    """Register a new authorized voice."""
    sec = _load_security()
    fp_hash = hash_voice_fingerprint(audio_features)
    
    # Check if already registered
    existing = [v for v in sec["voice_fingerprints"] if v["hash"] == fp_hash]
    if existing:
        return f"Voice '{existing[0]['label']}' is already registered."
    
    sec["voice_fingerprints"].append({
        "hash": fp_hash,
        "label": label,
        "added": datetime.now().isoformat(),
    })
    _save_security(sec)
    return f"✅ Voice '{label}' registered. I'll only respond to authorized voices."


def remove_voice(label: str = "", fingerprint: str = "") -> str:
    """Remove an authorized voice."""
    sec = _load_security()
    original = len(sec["voice_fingerprints"])
    
    if label:
        sec["voice_fingerprints"] = [
            v for v in sec["voice_fingerprints"] if v["label"].lower() != label.lower()
        ]
    elif fingerprint:
        sec["voice_fingerprints"] = [
            v for v in sec["voice_fingerprints"] if v["hash"] != fingerprint
        ]
    
    if len(sec["voice_fingerprints"]) < original:
        _save_security(sec)
        removed = original - len(sec["voice_fingerprints"])
        return f"🗑️ Removed {removed} authorized voice(s)."
    return "No matching voice found."


def list_voices() -> str:
    """List all authorized voices."""
    sec = _load_security()
    if not sec["voice_fingerprints"]:
        return "No authorized voices registered. Use 'register_voice' to add one."
    
    lines = [f"🎤 **{len(sec['voice_fingerprints'])} authorized voice(s):**\n"]
    for v in sec["voice_fingerprints"]:
        lines.append(f"  • {v['label']} (added {v['added'][:10]})")
    return "\n".join(lines)


# ── Voice Verification ──────────────────────────────────────────

def verify_voice(audio_features: str) -> dict:
    """
    Check if a voice is authorized.
    
    Returns:
        {"authorized": bool, "voice_label": str or None, "confidence": float}
    """
    sec = _load_security()
    
    if not sec["voice_lock_enabled"]:
        return {"authorized": True, "voice_label": None, "confidence": 1.0}
    
    if not sec["voice_fingerprints"]:
        # Lock enabled but no voices registered — deny everyone
        return {"authorized": False, "voice_label": None, "confidence": 0.0}
    
    # Check lockout
    if sec.get("lockout_until"):
        lockout_time = datetime.fromisoformat(sec["lockout_until"])
        if datetime.now() < lockout_time:
            remaining = (lockout_time - datetime.now()).seconds // 60
            return {"authorized": False, "voice_label": None, "confidence": 0.0,
                    "message": f"Locked out. Try again in {remaining} min."}
        else:
            sec["lockout_until"] = None
            _save_security(sec)
    
    fp_hash = hash_voice_fingerprint(audio_features)
    for v in sec["voice_fingerprints"]:
        if v["hash"] == fp_hash:
            return {"authorized": True, "voice_label": v["label"], "confidence": 0.9}
    
    return {"authorized": False, "voice_label": None, "confidence": 0.0}


# ── PIN Code Access ─────────────────────────────────────────────

def set_pin(pin: str) -> str:
    """Set or update the backup PIN code."""
    if len(pin) < 4 or len(pin) > 8:
        return "PIN must be 4-8 digits."
    sec = _load_security()
    sec["pin_code"] = hashlib.sha256(pin.encode()).hexdigest()
    _save_security(sec)
    return f"✅ PIN set. You can use it as a backup to unlock the agent."


def verify_pin(pin: str) -> bool:
    """Verify a PIN code."""
    sec = _load_security()
    if not sec["pin_code"]:
        return True  # No PIN set = access allowed
    return hashlib.sha256(pin.encode()).hexdigest() == sec["pin_code"]


def remove_pin() -> str:
    """Remove the PIN code."""
    sec = _load_security()
    sec["pin_code"] = ""
    _save_security(sec)
    return "✅ PIN removed."


# ── Session Tokens ──────────────────────────────────────────────

def create_session(voice_label: str = "text") -> str:
    """Create an authenticated session token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user": voice_label,
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
    }
    return token


def verify_session(token: str) -> bool:
    """Check if a session token is valid."""
    if not token:
        return not _user_settings_has_lock()
    session = _sessions.get(token)
    if not session:
        return not _user_settings_has_lock()
    if time.time() > session["expires_at"]:
        del _sessions[token]
        return False
    return True


def _user_settings_has_lock() -> bool:
    """Check if any lock mechanism is active."""
    sec = _load_security()
    return sec["voice_lock_enabled"] or bool(sec["pin_code"])


def get_security_status() -> str:
    """Human-readable security status."""
    sec = _load_security()
    lines = ["🔒 **Security Status:**\n"]
    lines.append(f"  Voice lock: {'🟢 Enabled' if sec['voice_lock_enabled'] else '⚪ Disabled'}")
    lines.append(f"  Authorized voices: {len(sec['voice_fingerprints'])}")
    lines.append(f"  PIN code: {'🟢 Set' if sec['pin_code'] else '⚪ Not set'}")
    lines.append(f"  Active sessions: {len(_sessions)}")
    
    if sec["lockout_until"]:
        lines.append(f"  ⚠️ Lockout until: {sec['lockout_until']}")
    
    if not sec["voice_lock_enabled"] and not sec["pin_code"]:
        lines.append("\n💡 No security locks active. Anyone can access the agent.")
        lines.append("   Enable voice lock or set a PIN to secure it.")
    
    return "\n".join(lines)
