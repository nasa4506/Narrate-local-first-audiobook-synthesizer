"""
Voice catalog definitions for Kokoro-82M TTS.
Maps language codes to available voices with human-readable descriptions.
"""

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
    "storytelling": {
        "label": "📖 Storytelling",
        "text": "Once upon a time in a distant digital galaxy, an extraordinary 82-million parameter voice engine was born. It spoke with human clarity and warmth, right from a local machine."
    },
    "product_launch": {
        "label": "⚡ Product Launch",
        "text": "Introducing Kokoro-82M, an ultra-lightweight open-source text-to-speech model. Operating completely offline with zero API latency and incredible natural audio fidelity."
    },
    "conversational": {
        "label": "🗣️ Conversational",
        "text": "Hey there! How is your day going? I'm testing out speech synthesis locally on Windows. Pretty impressive, isn't it?"
    },
    "multilingual": {
        "label": "🌍 Multilingual",
        "text": "Hello and welcome! ¡Hola y bienvenido! Bonjour et bienvenue! Ciao e benvenuto! Namaste!"
    },
}
