import os

from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:
    pass
else:
    # On Streamlit Community Cloud, secrets are configured in the app's
    # dashboard (not a committed .env) and surface via st.secrets. Mirror
    # flat string secrets (e.g. GEMINI_API_KEY = "...") into os.environ so
    # the rest of the app stays deployment-agnostic. Nested [section] tables
    # aren't flattened - declare secrets as flat top-level keys.
    try:
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except StreamlitSecretNotFoundError:
        pass  # no secrets.toml configured - fine for local dev via .env
