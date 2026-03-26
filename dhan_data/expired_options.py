import logging

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit not available in some contexts
    st = None

_logger = logging.getLogger(__name__)


def _show_info(message):
    if st is None:
        return
    try:
        st.info(message)
    except Exception:
        pass


def get_expired_options(security_id, segment, option_type="CALL"):
    """Expired options data is not available via the Dhan data APIs."""
    _logger.warning(
        "Expired options not supported via Dhan data APIs (security_id=%s, segment=%s, option_type=%s).",
        security_id,
        segment,
        option_type,
    )
    _show_info("Expired options data is not supported by the Dhan data APIs.")
    return None
