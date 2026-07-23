"""CodexSaver: cost-aware LLM delegation for Codex."""

__version__ = "0.3.6"

# Install the fail-closed work-packet recipe boundary before callers import
# codexsaver.engine or codexsaver.work_packet directly.
from .work_packet_guard import install_work_packet_guard as _install_work_packet_guard

_install_work_packet_guard()
del _install_work_packet_guard
