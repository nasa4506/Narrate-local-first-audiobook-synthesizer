import io
import time
import torch
import numpy as np
import soundfile as sf
import streamlit as st
from kokoro import KPipeline

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Kokoro-82M TTS Studio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium UI
st.markdown("""
<style>
    /* Dark glassmorphism theme styling */
    .stApp {
        background: linear-gradient(135deg, #0b0d17 0%, #111428 50%, #0d0e1a 100%);
        color: #e2e8f0;
    }
    
    /* Header Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 28px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 16px;
    }
    
    /* Badge Pills */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        background: rgba(99, 102, 241, 0.2);
        border: 1px solid rgba(99, 102, 241, 0.4);
        color: #a5b4fc;
    }
    .badge-success {
        background: rgba(34, 197, 94, 0.2);
        border-color: rgba(34, 197, 94, 0.4);
        color: #86efac;
    }
    .badge-gpu {
        background: rgba(234, 179, 8, 0.2);
        border-color: rgba(234, 179, 8, 0.5);
        color: #fde047;
    }
    .badge-info {
        background: rgba(56, 189, 248, 0.2);
        border-color: rgba(56, 189, 248, 0.4);
        color: #7dd3fc;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
    }

    /* Phoneme display box */
    .phoneme-box {
        font-family: 'Courier New', Courier, monospace;
        background: rgba(15, 23, 42, 0.8);
        border-left: 4px solid #818cf8;
        padding: 12px 16px;
        border-radius: 6px;
        color: #e2e8f0;
        font-size: 0.95rem;
        word-break: break-all;
    }

    /* Sidebar tweaks */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Voice Catalog & Mapping
# ---------------------------------------------------------
VOICE_CATALOG = {
    "a": {
        "name": "American English 🇺🇸",
        "voices": {
            "af_heart": "Female - Heart (Clear & Expressive - Default)",
            "af_bella": "Female - Bella (Warm & Gentle)",
            "af_nicole": "Female - Nicole (Casual)",
            "af_aoede": "Female - Aoede (Soft)",
            "af_kore": "Female - Kore (Natural)",
            "af_sarah": "Female - Sarah (Bright)",
            "af_sky": "Female - Sky (Airy)",
            "af_alloy": "Female - Alloy (Neutral)",
            "af_jessica": "Female - Jessica (Friendly)",
            "af_nova": "Female - Nova (Dynamic)",
            "af_river": "Female - River (Calm)",
            "am_adam": "Male - Adam (Deep & Authoritative)",
            "am_michael": "Male - Michael (Friendly)",
            "am_fenrir": "Male - Fenrir (Resonant)",
            "am_puck": "Male - Puck (Energetic)",
            "am_echo": "Male - Echo (Smooth)",
            "am_eric": "Male - Eric (Professional)",
            "am_liam": "Male - Liam (Warm)",
            "am_onyx": "Male - Onyx (Deep)",
            "am_santa": "Male - Santa (Joyful)",
        }
    },
    "b": {
        "name": "British English 🇬🇧",
        "voices": {
            "bf_emma": "Female - Emma (Refined British)",
            "bf_isabella": "Female - Isabella (Clear British)",
            "bf_alice": "Female - Alice (Gentle British)",
            "bf_lily": "Female - Lily (Melodic British)",
            "bm_george": "Male - George (Classic British)",
            "bm_fable": "Male - Fable (Storyteller British)",
            "bm_lewis": "Male - Lewis (Modern British)",
            "bm_daniel": "Male - Daniel (Deep British)",
        }
    },
    "e": {
        "name": "Spanish 🇪🇸",
        "voices": {
            "ef_dora": "Female - Dora",
            "em_alex": "Male - Alex",
            "em_santa": "Male - Santa",
        }
    },
    "f": {
        "name": "French 🇫🇷",
        "voices": {
            "ff_siwis": "Female - Siwis",
        }
    },
    "h": {
        "name": "Hindi 🇮🇳",
        "voices": {
            "hf_alpha": "Female - Alpha",
            "hf_beta": "Female - Beta",
            "hm_omega": "Male - Omega",
            "hm_psi": "Male - Psi",
        }
    },
    "i": {
        "name": "Italian 🇮🇹",
        "voices": {
            "if_sara": "Female - Sara",
            "im_nicola": "Male - Nicola",
        }
    },
    "p": {
        "name": "Portuguese 🇧🇷",
        "voices": {
            "pf_dora": "Female - Dora",
            "pm_alex": "Male - Alex",
            "pm_santa": "Male - Santa",
        }
    }
}

SAMPLE_PRESETS = {
    "📖 Storytelling": "Once upon a time in a distant digital galaxy, an extraordinary 82-million parameter voice engine was born. It spoke with human clarity and warmth, right from a local machine.",
    "⚡ Product Launch": "Introducing Kokoro-82M, an ultra-lightweight open-source text-to-speech model. Operating completely offline with zero API latency and incredible natural audio fidelity.",
    "🗣️ Conversational": "Hey there! How is your day going? I'm testing out speech synthesis locally on Windows. Pretty impressive, isn't it?",
    "🌍 Multilingual": "Hello and welcome! ¡Hola y bienvenido! Bonjour et bienvenue! Ciao e benvenuto! Namaste!",
}

# ---------------------------------------------------------
# Cached Model Pipeline Loader
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_pipeline(lang_code: str, device: str):
    """Loads and caches Kokoro KPipeline for the chosen language and compute device."""
    return KPipeline(lang_code=lang_code, device=device)

def generate_speech(pipeline, text: str, voice_arg, speed: float):
    """Executes TTS pipeline and returns concatenated audio array & phonemes."""
    t0 = time.time()
    generator = pipeline(text, voice=voice_arg, speed=speed)
    all_audio = []
    all_phonemes = []
    
    for gs, ps, audio in generator:
        if audio is not None and len(audio) > 0:
            all_audio.append(audio)
        if ps:
            all_phonemes.append(ps)
            
    gen_time = time.time() - t0
    
    if not all_audio:
        return None, "", 0.0, 0.0
        
    full_audio = np.concatenate(all_audio)
    phonemes_str = " | ".join(all_phonemes)
    duration_sec = len(full_audio) / 24000.0
    return full_audio, phonemes_str, gen_time, duration_sec

def audio_to_bytes(audio_array: np.ndarray, sample_rate: int = 24000) -> bytes:
    """Converts numpy audio array to in-memory WAV bytes."""
    buf = io.BytesIO()
    sf.write(buf, audio_array, sample_rate, format='WAV')
    return buf.getvalue()

# Initialize session state for audio history
if "history" not in st.session_state:
    st.session_state["history"] = []

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuration")

# Hardware Compute Device Selection
has_cuda = torch.cuda.is_available()
gpu_name = torch.cuda.get_device_name(0) if has_cuda else None

device_options = []
if has_cuda:
    device_options.append("cuda")
device_options.append("cpu")

selected_device = st.sidebar.radio(
    "Compute Device Target",
    options=device_options,
    format_func=lambda d: f"🚀 GPU (NVIDIA {gpu_name})" if d == "cuda" else "💻 CPU",
    index=0
)

mode = st.sidebar.radio(
    "Synthesis Mode",
    ["🎙️ Single Voice", "🎛️ Voice Blend Studio", "🧪 Voice Matrix (Compare)"],
    index=0
)

st.sidebar.markdown("---")

# Language Selection
lang_code = st.sidebar.selectbox(
    "Language & Region",
    options=list(VOICE_CATALOG.keys()),
    format_func=lambda k: VOICE_CATALOG[k]["name"],
    index=0
)

voices_dict = VOICE_CATALOG[lang_code]["voices"]

# Load pipeline with spinner
with st.spinner(f"Initializing Kokoro pipeline on {'GPU' if selected_device == 'cuda' else 'CPU'}..."):
    pipeline = load_pipeline(lang_code, selected_device)

if mode == "🎙️ Single Voice":
    selected_voice_key = st.sidebar.selectbox(
        "Select Voice",
        options=list(voices_dict.keys()),
        format_func=lambda k: f"{k} ({voices_dict[k]})"
    )
elif mode == "🎛️ Voice Blend Studio":
    st.sidebar.subheader("Blend Two Voices")
    voice_a_key = st.sidebar.selectbox(
        "Primary Voice (Voice A)",
        options=list(voices_dict.keys()),
        index=0,
        format_func=lambda k: f"{k} ({voices_dict[k]})"
    )
    voice_b_key = st.sidebar.selectbox(
        "Secondary Voice (Voice B)",
        options=list(voices_dict.keys()),
        index=min(1, len(voices_dict) - 1),
        format_func=lambda k: f"{k} ({voices_dict[k]})"
    )
    blend_ratio = st.sidebar.slider(
        "Blend Mix Ratio (Voice A %)",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        help="0.7 means 70% Voice A + 30% Voice B"
    )
    st.sidebar.info(f"Mixing: {int(blend_ratio*100)}% {voice_a_key} + {int((1-blend_ratio)*100)}% {voice_b_key}")
elif mode == "🧪 Voice Matrix (Compare)":
    st.sidebar.subheader("Select Voices to Compare")
    compare_voices = st.sidebar.multiselect(
        "Choose Voices",
        options=list(voices_dict.keys()),
        default=list(voices_dict.keys())[:3],
        format_func=lambda k: f"{k} ({voices_dict[k]})"
    )

st.sidebar.markdown("---")

# Speed Control
speech_speed = st.sidebar.slider(
    "Speech Speed",
    min_value=0.5,
    max_value=2.0,
    value=1.0,
    step=0.05,
    format="%.2fx"
)

# ---------------------------------------------------------
# UI Header
# ---------------------------------------------------------
device_badge = f'<span class="badge badge-gpu">🚀 Active: NVIDIA {gpu_name} (GPU)</span>' if selected_device == 'cuda' else '<span class="badge badge-info">💻 Active: CPU</span>'

st.markdown(f"""
<div class="hero-container">
    <div class="hero-title">🎙️ Kokoro-82M TTS Studio</div>
    <div class="hero-subtitle">High-quality, lightweight local Text-to-Speech powered by hexgrad Kokoro-82M</div>
    <div>
        <span class="badge badge-success">● Model: Kokoro-82M</span>
        {device_badge}
        <span class="badge">🎵 Sample Rate: 24kHz</span>
        <span class="badge">🌐 50+ Voices</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Main Workspace: Text Input & Presets
# ---------------------------------------------------------
st.subheader("📝 Input Text")

# Preset buttons row
cols = st.columns(len(SAMPLE_PRESETS))
preset_text = None
for i, (label, sample) in enumerate(SAMPLE_PRESETS.items()):
    if cols[i].button(label, use_container_width=True):
        preset_text = sample

# Main text area
default_input = preset_text if preset_text else "Kokoro is a lightweight open-source text-to-speech model with 82 million parameters. It generates amazingly natural and fluent voice audio directly on your local machine."

input_mode = st.tabs(["✍️ Custom Text", "📁 File Upload (.txt)"])

with input_mode[0]:
    user_text = st.text_area(
        "Enter text to synthesize:",
        value=default_input,
        height=140,
        placeholder="Type or paste text here..."
    )

with input_mode[1]:
    uploaded_file = st.file_uploader("Upload a text file", type=["txt"])
    if uploaded_file is not None:
        file_text = uploaded_file.read().decode("utf-8")
        st.success(f"Loaded {len(file_text)} characters from {uploaded_file.name}")
        user_text = st.text_area("File Content Preview:", value=file_text, height=140)

# Synthesize Button
generate_btn = st.button("⚡ Generate Speech", type="primary", use_container_width=True)

# ---------------------------------------------------------
# Execution & Results
# ---------------------------------------------------------
if generate_btn:
    if not user_text.strip():
        st.warning("Please enter or upload some text to synthesize.")
    else:
        if mode == "🎙️ Single Voice":
            with st.spinner(f"Synthesizing with {selected_voice_key} on {selected_device.upper()}..."):
                audio, phonemes, gen_time, duration = generate_speech(
                    pipeline, user_text, selected_voice_key, speech_speed
                )
                
            if audio is not None:
                wav_bytes = audio_to_bytes(audio)
                rtf = gen_time / duration if duration > 0 else 0
                
                # Metrics Row
                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{gen_time:.2f}s</div>
                    <div class="metric-label">Generation Time</div>
                </div>
                """, unsafe_allow_html=True)
                
                m2.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{duration:.2f}s</div>
                    <div class="metric-label">Audio Duration</div>
                </div>
                """, unsafe_allow_html=True)
                
                m3.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{rtf:.2f}x</div>
                    <div class="metric-label">Real-Time Factor (RTF)</div>
                </div>
                """, unsafe_allow_html=True)
                
                m4.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{selected_device.upper()}</div>
                    <div class="metric-label">Compute Device</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Audio Player & Download
                c_player, c_dl = st.columns([3, 1])
                with c_player:
                    st.audio(wav_bytes, format="audio/wav")
                with c_dl:
                    st.download_button(
                        label="⬇️ Download WAV",
                        data=wav_bytes,
                        file_name=f"kokoro_{selected_voice_key}_{int(time.time())}.wav",
                        mime="audio/wav",
                        use_container_width=True
                    )
                    
                # Phoneme display tab
                with st.expander("🗣️ View Generated Phonemes & Transcript", expanded=True):
                    st.markdown(f'<div class="phoneme-box">{phonemes}</div>', unsafe_allow_html=True)
                    
                # Save to history
                st.session_state["history"].insert(0, {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "voice": selected_voice_key,
                    "mode": "Single",
                    "text": user_text[:60] + ("..." if len(user_text) > 60 else ""),
                    "duration": f"{duration:.2f}s",
                    "bytes": wav_bytes
                })

        elif mode == "🎛️ Voice Blend Studio":
            with st.spinner(f"Blending {voice_a_key} ({int(blend_ratio*100)}%) + {voice_b_key} ({int((1-blend_ratio)*100)}%)..."):
                v1 = pipeline.load_voice(voice_a_key)
                v2 = pipeline.load_voice(voice_b_key)
                blended_voice = blend_ratio * v1 + (1.0 - blend_ratio) * v2
                
                audio, phonemes, gen_time, duration = generate_speech(
                    pipeline, user_text, blended_voice, speech_speed
                )
                
            if audio is not None:
                wav_bytes = audio_to_bytes(audio)
                rtf = gen_time / duration if duration > 0 else 0
                blend_name = f"{int(blend_ratio*100)}%{voice_a_key} + {int((1-blend_ratio)*100)}%{voice_b_key}"
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Generation Time", f"{gen_time:.2f} sec")
                m2.metric("Audio Duration", f"{duration:.2f} sec")
                m3.metric("RTF (Speed Ratio)", f"{rtf:.2f}x")
                
                c_player, c_dl = st.columns([3, 1])
                with c_player:
                    st.audio(wav_bytes, format="audio/wav")
                with c_dl:
                    st.download_button(
                        label="⬇️ Download Blend WAV",
                        data=wav_bytes,
                        file_name=f"kokoro_blend_{int(time.time())}.wav",
                        mime="audio/wav",
                        use_container_width=True
                    )
                    
                with st.expander("🗣️ View Phonemes"):
                    st.markdown(f'<div class="phoneme-box">{phonemes}</div>', unsafe_allow_html=True)
                    
                st.session_state["history"].insert(0, {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "voice": blend_name,
                    "mode": "Blend",
                    "text": user_text[:60] + ("..." if len(user_text) > 60 else ""),
                    "duration": f"{duration:.2f}s",
                    "bytes": wav_bytes
                })

        elif mode == "🧪 Voice Matrix (Compare)":
            if not compare_voices:
                st.warning("Please select at least one voice from the sidebar to compare.")
            else:
                st.markdown("### 🧪 Voice Comparison Results")
                for v_key in compare_voices:
                    st.markdown(f"#### 🎙️ Voice: `{v_key}` ({voices_dict.get(v_key, '')})")
                    audio, phonemes, gen_time, duration = generate_speech(
                        pipeline, user_text, v_key, speech_speed
                    )
                    if audio is not None:
                        wav_bytes = audio_to_bytes(audio)
                        c_play, c_info, c_down = st.columns([3, 2, 1])
                        with c_play:
                            st.audio(wav_bytes, format="audio/wav")
                        with c_info:
                            st.caption(f"Time: {gen_time:.2f}s | Length: {duration:.2f}s")
                        with c_down:
                            st.download_button(
                                "⬇️ WAV",
                                data=wav_bytes,
                                file_name=f"{v_key}.wav",
                                mime="audio/wav",
                                key=f"dl_{v_key}"
                            )

# ---------------------------------------------------------
# Audio History Gallery
# ---------------------------------------------------------
if st.session_state["history"]:
    st.markdown("---")
    st.subheader("📜 Session Audio History Gallery")
    
    for idx, item in enumerate(st.session_state["history"]):
        with st.expander(f"🔊 [{item['timestamp']}] {item['voice']} ({item['mode']}) — {item['duration']}", expanded=(idx == 0)):
            st.write(f"**Text:** {item['text']}")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.audio(item["bytes"], format="audio/wav")
            with c2:
                st.download_button(
                    "⬇️ Download",
                    data=item["bytes"],
                    file_name=f"history_{idx}.wav",
                    mime="audio/wav",
                    key=f"hist_dl_{idx}",
                    use_container_width=True
                )
