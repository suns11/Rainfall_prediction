# services/voice.py

import io
import re
import hashlib

import streamlit as st
from gtts import gTTS


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def _init_voice_state():
    defaults = {
        "voice_audio": None,
        "voice_version": 0,
        "voice_rendered_version": -1,
        "voice_hash": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# BANGLA TEXT CLEANER
# ============================================================

def clean_voice_text(text):
    """
    TTS-এর জন্য শুধুমাত্র Bangla অংশ রাখে।

    English UI text বাদ যাবে:
        ET0
        Acre
        Hectare
        Drip
        Sprinkler
        Traditional
        Rice
        Tomato
        etc.

    Bangla:
        থাকবে

    Bangla digits:
        থাকবে
    """

    if text is None:
        return ""

    text = str(text)

    # --------------------------------------------------------
    # HTML / TAG REMOVE
    # --------------------------------------------------------

    text = re.sub(r"<[^>]+>", " ", text)

    # --------------------------------------------------------
    # URL / EMAIL REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\S+@\S+\.\S+",
        " ",
        text
    )

    # --------------------------------------------------------
    # ENGLISH WORDS REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"[A-Za-z]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # COMMON SYMBOLS REMOVE
    # --------------------------------------------------------

    text = re.sub(
        r"[_|/\\]+",
        " ",
        text
    )

    # Keep:
    # Bangla Unicode
    # Bangla digits
    # English digits
    # Bangla punctuation
    # Normal punctuation

    text = re.sub(
        r"[^\u0980-\u09FF\u09E6-\u09EF0-9\s।,!?;:%\-–—()]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # REMOVE EXTRA PUNCTUATION
    # --------------------------------------------------------

    text = re.sub(
        r"[-–—]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # NORMALIZE SPACES
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# BANGLA NUMBER CONVERSION
# ============================================================

def _english_digits_to_bangla(text):
    table = str.maketrans(
        "0123456789",
        "০১২৩৪৫৬৭৮৯"
    )

    return text.translate(table)


# ============================================================
# PREPARE VOICE TEXT
# ============================================================

def _prepare_voice_text(text):
    """
    Voice-এর আগে English বাদ দিয়ে Bangla text তৈরি করে।
    """

    text = clean_voice_text(text)

    if not text:
        return ""

    # English numbers → Bangla numbers
    text = _english_digits_to_bangla(text)

    # Extra spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# GENERATE MP3
# ============================================================

def _generate_audio(text):
    """
    gTTS দিয়ে Bangla MP3 তৈরি করে।
    """

    clean_text = _prepare_voice_text(text)

    if not clean_text:
        return None

    try:
        audio_buffer = io.BytesIO()

        tts = gTTS(
            text=clean_text,
            lang="bn",
            slow=False
        )

        tts.write_to_fp(audio_buffer)

        audio_buffer.seek(0)

        return audio_buffer.getvalue()

    except Exception:
        return None


# ============================================================
# SPEAK SEQUENCE
# ============================================================

def speak_sequence(messages, delay=0.0):
    """
    একাধিক voice message একসাথে একটি audio file হিসেবে তৈরি করে।

    এতে:
        - voice overlap হবে না
        - multiple audio player হবে না
        - English text পড়বে না
        - browser-side audio হবে
    """

    _init_voice_state()

    if not messages:
        return

    prepared_messages = []

    for message in messages:

        cleaned = _prepare_voice_text(message)

        if cleaned:
            prepared_messages.append(cleaned)

    if not prepared_messages:
        return

    # --------------------------------------------------------
    # একাধিক sentence একসাথে
    # --------------------------------------------------------

    final_text = " । ".join(
        prepared_messages
    )

    # --------------------------------------------------------
    # Same voice হলে আবার generate না করা
    # --------------------------------------------------------

    voice_hash = hashlib.md5(
        final_text.encode("utf-8")
    ).hexdigest()

    if st.session_state.get("voice_hash") == voice_hash:
        return

    audio = _generate_audio(final_text)

    if audio is None:
        return

    # --------------------------------------------------------
    # Store audio
    # --------------------------------------------------------

    st.session_state["voice_audio"] = audio
    st.session_state["voice_hash"] = voice_hash

    st.session_state["voice_version"] = (
        st.session_state.get("voice_version", 0) + 1
    )


# ============================================================
# SIMPLE SINGLE VOICE
# ============================================================

def speak(text, delay=0.0):
    """
    Single Bangla voice.
    """

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# PLAY VOICE
# ============================================================

def play_voice(text, delay=0.0):
    """
    Backward compatibility.
    """

    speak(
        text,
        delay=delay
    )


# ============================================================
# WELCOME VOICE
# ============================================================

def play_welcome(text):
    """
    Welcome voice.
    """

    speak_sequence(
        [text],
        delay=0.10
    )


# ============================================================
# SELECTION VOICE
# ============================================================

def selection_voice(
    text,
    value=None,
    key=None,
    delay=0.12
):
    """
    Selection change-এর Bangla confirmation voice.
    """

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# SECTION VOICE
# ============================================================

def section_voice(
    text,
    key=None,
    delay=0.10
):
    """
    Section heading / instruction voice.
    """

    if not text:
        return

    speak_sequence(
        [text],
        delay=delay
    )


# ============================================================
# PROCESS VOICE QUEUE
# ============================================================

def process_voice_queue():
    """
    Compatibility function.

    বর্তমানে আলাদা queue/thread দরকার নেই।
    speak_sequence সরাসরি audio তৈরি করে।
    """

    _init_voice_state()


# ============================================================
# BROWSER VOICE PLAYER
# ============================================================

def render_voice_player():
    """
    Browser-এর ভিতরে Bangla audio play করবে।

    Streamlit Cloud compatible.
    Server-side playsound ব্যবহার করা হচ্ছে না।
    """

    _init_voice_state()

    audio = st.session_state.get(
        "voice_audio"
    )

    version = st.session_state.get(
        "voice_version",
        0
    )

    rendered_version = st.session_state.get(
        "voice_rendered_version",
        -1
    )

    if not audio:
        return

    # একই audio বারবার play করবে না
    if version == rendered_version:
        return

    # Mark as rendered
    st.session_state[
        "voice_rendered_version"
    ] = version

    # Browser-side audio
    st.audio(
        audio,
        format="audio/mp3",
        autoplay=True
    )


# ============================================================
# CANCEL CURRENT VOICE
# ============================================================

def cancel_pending_voice():
    """
    Current voice reset.
    """

    _init_voice_state()

    st.session_state["voice_audio"] = None
    st.session_state["voice_hash"] = None

    st.session_state["voice_version"] = (
        st.session_state.get("voice_version", 0) + 1
    )


# ============================================================
# RESET VOICE STATE
# ============================================================

def reset_voice_state():
    """
    Completely reset voice session state.
    """

    st.session_state["voice_audio"] = None
    st.session_state["voice_hash"] = None
    st.session_state["voice_version"] = 0
    st.session_state["voice_rendered_version"] = -1