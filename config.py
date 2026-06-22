
import math
import os
import re


SHIPSGO_BASE_URL = os.getenv(
    "SHIPSGO_BASE_URL",
    "https://api.shipsgo.com/v2",
).rstrip("/")

API_TIMEOUT_SECONDS = int(
    os.getenv("SHIPSGO_API_TIMEOUT", "30")
)

LIST_PAGE_SIZE = int(
    os.getenv("SHIPSGO_LIST_PAGE_SIZE", "100")
)

MAX_BLS_PER_UPLOAD = int(
    os.getenv("MAX_BLS_PER_UPLOAD", "100")
)


# Tested automatic carrier detection rules.
# Other carrier codes can be entered manually in the review table.
CARRIER_PREFIX_MAP = {
    "ONEY": "ONEY",
    "MEDU": "MSCU",
    "MSCU": "MSCU",
}


def get_shipsgo_token() -> str:
    token = os.getenv(
        "SHIPSGO_API_TOKEN",
        "",
    ).strip()

    if not token:
        raise RuntimeError(
            "The API token is not configured."
        )

    return token


def normalize_number(
    value: object,
) -> str:
    if value is None:
        return ""

    if (
        isinstance(value, float)
        and math.isnan(value)
    ):
        return ""

    text = str(value).strip()

    if text.lower() in {
        "",
        "nan",
        "none",
        "<na>",
    }:
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        text.upper(),
    )


def detect_carrier_scac(
    bl_number: object,
) -> str:
    normalized_bl = normalize_number(
        bl_number
    )

    if len(normalized_bl) < 4:
        return ""

    return CARRIER_PREFIX_MAP.get(
        normalized_bl[:4],
        "",
    )

