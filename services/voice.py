import streamlit as st
from gtts import gTTS

import os
import hashlib
import threading
import time
import re
import base64


# ============================================================
# VOICE CACHE
# ============================================================

VOICE_CACHE_DIR = "voice_cache"
os.makedirs(VOICE_CACHE_DIR, exist_ok=True)

_VOICE_FILE_CACHE = {}

_VOICE_GENERATION_LOCK = threading.Lock()

_VOICE_STATE_LOCK = threading.Lock()
_VOICE_TOKEN = 0

_SELECTION_LOCK = threading.Lock()
_LAST_SELECTION_TEXT = {}

_SECTION_LOCK = threading.Lock()
_LAST_SECTION_TEXT = {}

_WELCOME_LOCK = threading.Lock()
_WELCOME_PLAYING = False
_WELCOME_PLAYED = False


BANGLA_RANGE = r"\u0980-\u09FF"


# ============================================================
# BANGLA DETECTION
# ============================================================

def contains_bangla(text):

    if text is None:
        return False

    return re.search(
        f"[{BANGLA_RANGE}]",
        str(text)
    ) is not None


# ============================================================
# CLEAN VOICE TEXT
# ============================================================

def clean_voice_text(text):

    if text is None:
        return ""

    text = str(text).strip()

    if not text:
        return ""

    english_patterns = [

        r"\bSelect\b",
        r"\bselected\b",
        r"\bselection\b",

        r"\bCrop\b",
        r"\bSeason\b",
        r"\bSoil\b",
        r"\bWater\b",

        r"\bRainfall\b",
        r"\bPrediction\b",
        r"\bPredicted\b",

        r"\bIrrigation\b",
        r"\bMethod\b",

        r"\bTraditional\b",
        r"\bSprinkler\b",
        r"\bDrip\b",

        r"\bCustom\b",
        r"\bMeasurement\b",
        r"\bCalculate\b",

        r"\bSmart\b",
        r"\bAgriculture\b",
        r"\bRecommendation\b",

        r"\bAutomatic\b",
        r"\bManual\b",
        r"\bOverride\b",

        r"\bRecommended\b",

        r"\bET0\b",
        r"\bETc\b",
        r"\bKc\b",

        r"\bmm\b",
        r"\bday\b",
        r"\bDaily\b",

        r"\bReference\b",
        r"\bEvapotranspiration\b",

        r"\bInformation\b",
        r"\bInput\b",
        r"\bOutput\b",
        r"\bResult\b",
        r"\bDetails\b",
        r"\bCurrent\b",

        r"\bStage\b",
        r"\bGrowth\b",

        r"\bInitial\b",
        r"\bDevelopment\b",
        r"\bMid\b",
        r"\bLate\b",

        r"\bArea\b",
        r"\bUnit\b",
        r"\bLand\b",

        r"\bExisting\b",
        r"\bEfficiency\b",

        r"\bPlanting\b",
        r"\bSowing\b",
        r"\bToday's\b",

    ]

    for pattern in english_patterns:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    # Remove English characters
    text = re.sub(
        r"[A-Za-z]+",
        "",
        text
    )

    # Remove unwanted symbols
    text = re.sub(
        r"[_|<>]+",
        " ",
        text
    )

    # Normalize spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# FILE NAME
# ============================================================

def get_voice_filename(text):

    text = str(text)

    text_hash = hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()

    return os.path.join(
        VOICE_CACHE_DIR,
        f"{text_hash}.mp3"
    )


# ============================================================
# GENERATE TTS
# ============================================================

def generate_voice(text):

    text = clean_voice_text(text)

    if not text:
        return None

    cached = _VOICE_FILE_CACHE.get(text)

    if cached and os.path.exists(cached):
        return cached

    filename = get_voice_filename(text)

    if os.path.exists(filename):

        _VOICE_FILE_CACHE[text] = filename

        return filename

    try:

        with _VOICE_GENERATION_LOCK:

            if os.path.exists(filename):

                _VOICE_FILE_CACHE[text] = filename

                return filename

            tts = gTTS(
                text=text,
                lang="bn"
            )

            tts.save(filename)

        _VOICE_FILE_CACHE[text] = filename

        return filename

    except Exception as e:

        print(
            "Voice Generate Error:",
            e
        )

        return None


# ============================================================
# STREAMLIT BROWSER AUDIO
# ============================================================

def _browser_play_audio(filename, autoplay=True):

    if not filename:
        return False

    try:

        if not os.path.exists(filename):
            return False

        with open(
            filename,
            "rb"
        ) as audio_file:

            audio_bytes = audio_file.read()

        audio_base64 = base64.b64encode(
            audio_bytes
        ).decode()

        autoplay_value = "autoplay" if autoplay else ""

        audio_html = f"""
        <audio
            {autoplay_value}
            controls
            style="width:100%;"
        >
            <source
                src="data:audio/mp3;base64,{audio_base64}"
                type="audio/mp3"
            >
        </audio>
        """

        st.markdown(
            audio_html,
            unsafe_allow_html=True
        )

        return True

    except Exception as e:

        print(
            "Browser Audio Error:",
            e
        )

        return False


# ============================================================
# TOKEN SYSTEM
# ============================================================

def _new_voice_token():

    global _VOICE_TOKEN

    with _VOICE_STATE_LOCK:

        _VOICE_TOKEN += 1

        return _VOICE_TOKEN


def _voice_token_valid(token):

    with _VOICE_STATE_LOCK:

        return token == _VOICE_TOKEN


def cancel_pending_voice():

    _new_voice_token()


# ============================================================
# STREAMLIT VOICE PLAYER
# ============================================================

def _play_file(filename, token=None):

    if not filename:
        return False

    if token is not None:

        if not _voice_token_valid(token):
            return False

    return _browser_play_audio(
        filename,
        autoplay=True
    )


# ============================================================
# WELCOME VOICE
# ============================================================

def play_welcome(text, delay=0.5):

    global _WELCOME_PLAYING
    global _WELCOME_PLAYED

    with _WELCOME_LOCK:

        if _WELCOME_PLAYED:
            return

        _WELCOME_PLAYED = True
        _WELCOME_PLAYING = True

    filename = generate_voice(text)

    if filename:

        _browser_play_audio(
            filename,
            autoplay=True
        )

    with _WELCOME_LOCK:

        _WELCOME_PLAYING = False


def is_welcome_playing():

    with _WELCOME_LOCK:

        return _WELCOME_PLAYING


def reset_welcome_voice():

    global _WELCOME_PLAYING
    global _WELCOME_PLAYED

    with _WELCOME_LOCK:

        _WELCOME_PLAYING = False
        _WELCOME_PLAYED = False


# ============================================================
# WAIT FOR WELCOME
# ============================================================

def _wait_for_welcome(token):

    while is_welcome_playing():

        if not _voice_token_valid(token):

            return False

        time.sleep(0.08)

    return _voice_token_valid(token)


# ============================================================
# VOICE SEQUENCE
# ============================================================

def _run_voice_sequence(
    texts,
    delay=0.10
):

    clean_texts = []

    for text in texts:

        cleaned = clean_voice_text(text)

        if (
            cleaned
            and cleaned not in clean_texts
        ):

            clean_texts.append(cleaned)

    if not clean_texts:
        return

    token = _new_voice_token()

    # Streamlit browser rendering must happen
    # in the main Streamlit execution.
    #
    # Therefore we store the generated audio
    # in session state instead of using a
    # background playback thread.

    try:

        filenames = []

        for text in clean_texts:

            if not _voice_token_valid(token):

                return

            filename = generate_voice(text)

            if filename:

                filenames.append(filename)

        if not filenames:
            return

        if "voice_queue" not in st.session_state:

            st.session_state.voice_queue = []

        st.session_state.voice_queue = filenames

        st.session_state.voice_token = token

    except Exception as e:

        print(
            "Voice Sequence Error:",
            e
        )


# ============================================================
# SPEAK SEQUENCE
# ============================================================

def speak_sequence(
    texts,
    delay=0.05
):

    if isinstance(texts, str):

        texts = [texts]

    _run_voice_sequence(
        list(texts),
        delay=delay
    )


# ============================================================
# SECTION VOICE
# ============================================================

def section_voice(
    text,
    key="general_section",
    delay=0.10
):

    clean_text = clean_voice_text(text)

    if not clean_text:
        return

    with _SECTION_LOCK:

        previous_text = _LAST_SECTION_TEXT.get(key)

        if previous_text == clean_text:

            return

        _LAST_SECTION_TEXT[key] = clean_text

    _run_voice_sequence(
        [clean_text],
        delay=delay
    )


# ============================================================
# SELECTION VOICE
# ============================================================

def selection_voice(
    text,
    key="general",
    delay=0.10,
    intro_text=None
):

    clean_text = clean_voice_text(text)

    if not clean_text:
        return

    with _SELECTION_LOCK:

        previous_text = _LAST_SELECTION_TEXT.get(key)

        if previous_text == clean_text:

            return

        _LAST_SELECTION_TEXT[key] = clean_text

    sequence = []

    if intro_text:

        sequence.append(
            intro_text
        )

    sequence.append(
        clean_text
    )

    _run_voice_sequence(
        sequence,
        delay=delay
    )


# ============================================================
# RESET SECTION
# ============================================================

def reset_section_voice():

    global _LAST_SECTION_TEXT

    _new_voice_token()

    with _SECTION_LOCK:

        _LAST_SECTION_TEXT = {}


# ============================================================
# RESET SELECTION
# ============================================================

def reset_selection_voice():

    global _LAST_SELECTION_TEXT

    _new_voice_token()

    with _SELECTION_LOCK:

        _LAST_SELECTION_TEXT = {}


# ============================================================
# RESET EVERYTHING
# ============================================================

def reset_all_voice_states():

    global _LAST_SELECTION_TEXT
    global _LAST_SECTION_TEXT

    _new_voice_token()

    with _SELECTION_LOCK:

        _LAST_SELECTION_TEXT = {}

    with _SECTION_LOCK:

        _LAST_SECTION_TEXT = {}


# ============================================================
# SIMPLE VOICE
# ============================================================

def play_voice(
    text,
    delay=0.2
):

    _run_voice_sequence(
        [text],
        delay=delay
    )


def speak(text):

    play_voice(
        text,
        delay=0.2
    )


# ============================================================
# RENDER VOICE QUEUE
# ============================================================

def render_voice():

    if "voice_queue" not in st.session_state:
        return

    queue = st.session_state.voice_queue

    if not queue:
        return

    # Play first generated audio.
    filename = queue[0]

    _browser_play_audio(
        filename,
        autoplay=True
    )

    # Remove after rendering.
    st.session_state.voice_queue = queue[1:]