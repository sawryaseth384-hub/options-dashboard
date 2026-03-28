import logging


_logger = logging.getLogger(__name__)


def get_expired_options(security_id, segment, option_type="CALL"):
    """Expired options data is not available via the Dhan data APIs."""
    _logger.warning(
        "Expired options not supported via Dhan data APIs (security_id=%s, segment=%s, option_type=%s).",
        security_id,
        segment,
        option_type,
    )
    return None
