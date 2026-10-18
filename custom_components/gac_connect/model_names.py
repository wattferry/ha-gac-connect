"""Resolve the vehicle `model` value the library returns into a display name.

Most markets report `model` as a plain name string. The UK My AION backend
reports it as a numeric code instead, and the device/entity registries need a
plain string, so the code has to be mapped before it reaches them. Only codes
confirmed against a real vehicle are listed here; an unconfirmed code is
deliberately not guessed, since mislabelling an unknown vehicle is worse than
asking the user to report it.
"""
from __future__ import annotations

_CONFIRMED_MODEL_CODES: dict[str, str] = {
    "1": "AION V",
}


class UnrecognisedModelCode(ValueError):
    """A numeric vehicle model code with no confirmed mapping."""


def resolve_model_name(raw: object) -> str | None:
    """Return a plain model name for `raw`, or `None` if it is empty/missing.

    A non-empty, non-digit string (every market but the UK) is returned
    trimmed, unchanged. A digit string or an int is treated as a model code
    and looked up in `_CONFIRMED_MODEL_CODES`; an unrecognised code raises
    `UnrecognisedModelCode` rather than being guessed.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        name = raw.strip()
        if not name:
            return None
        if not name.isdigit():
            return name
        code = name
    else:
        code = str(raw).strip()
    try:
        return _CONFIRMED_MODEL_CODES[code]
    except KeyError:
        raise UnrecognisedModelCode(
            f"Unrecognised vehicle model code {code!r}. Only "
            f"{sorted(_CONFIRMED_MODEL_CODES)} are confirmed; refusing to guess "
            "the model of an unknown vehicle. Please report this code at "
            "https://github.com/wattferry/ha-gac-connect/issues."
        ) from None
