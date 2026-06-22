from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import requests

from config import (
    API_TIMEOUT_SECONDS,
    LIST_PAGE_SIZE,
    SHIPSGO_BASE_URL,
    detect_carrier_scac,
    get_shipsgo_token,
    normalize_number,
)


ProgressCallback = Callable[[int, int, str], None]


EVENT_LABELS = {
    "BOOK": "Booked",
    "GTIN": "Gate In",
    "LOAD": "Loaded on Vessel",
    "DEPA": "Vessel Departure",
    "ARRV": "Vessel Arrival",
    "DISC": "Discharged",
    "GTOT": "Gate Out",
    "EMPTY": "Empty Container Returned",
}


class TrackingAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def parse_iso(value: object) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    except (TypeError, ValueError):
        return None


def format_datetime(value: object) -> str:
    parsed = parse_iso(value)

    if parsed is not None:
        return parsed.strftime("%Y-%m-%d %H:%M")

    return str(value) if value else "N/A"


def calculate_eta_change(
    current_eta: object,
    initial_eta: object,
) -> int | str:
    current = parse_iso(current_eta)
    initial = parse_iso(initial_eta)

    if current is None or initial is None:
        return "N/A"

    return (current.date() - initial.date()).days


def extract_country_code(*sources: object) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue

        # 1. 딕셔너리 안에서 명확한 2자리 국가코드 찾기
        country = source.get("country")
        if isinstance(country, dict):
            for key in ("code", "iso2", "iso_2", "isoCode", "iso_code", "alpha2", "alpha_2"):
                val = str(country.get(key, "")).strip().upper()
                if len(val) == 2 and val.isalpha():
                    return val

        # 2. UNLOCODE(항구코드)에서 앞 2자리(국가코드) 추출하기 (가장 정확)
        for key in ("unlocode", "un_locode", "unLocode", "locode", "location_code", "locationCode"):
            val = str(source.get(key, "")).strip().upper()
            norm = "".join(c for c in val if c.isalnum())
            if len(norm) >= 4 and norm[:2].isalpha():
                return norm[:2]

        # 3. 직접적인 국가코드 키값 찾기
        for key in ("country_code", "countryCode", "iso2", "iso_2"):
            val = str(source.get(key, "")).strip().upper()
            if len(val) == 2 and val.isalpha():
                return val

        # 4. 코드가 없으면 N/A 대신 국가 이름(China 등)이라도 반환
        if isinstance(country, dict):
            name = str(country.get("name", "")).strip().upper()
            if name:
                return name
        elif isinstance(country, str) and country.strip():
            return country.strip().upper()

        for key in ("country_name", "countryName"):
            val = str(source.get(key, "")).strip().upper()
            if val:
                return val

    return "N/A"


def extract_location_name(
    port: object,
) -> str:
    if not isinstance(port, dict):
        return "N/A"

    location = (
        port.get("location", {})
        or {}
    )

    if isinstance(location, dict):
        name = (
            location.get("name")
            or location.get(
                "location_name"
            )
            or location.get(
                "locationName"
            )
        )

        if name:
            return str(name)

    name = (
        port.get("name")
        or port.get("port_name")
        or port.get("portName")
    )

    return str(name) if name else "N/A"


class OceanTrackingProvider:
    def __init__(self) -> None:
        self.base_url = SHIPSGO_BASE_URL
        self.session = requests.Session()

    def _headers(
        self,
    ) -> dict[str, str]:
        return {
            "X-Shipsgo-User-Token": (
                get_shipsgo_token()
            ),
            "Accept": (
                "application/json"
            ),
            "Content-Type": (
                "application/json"
            ),
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: (
            dict[str, Any] | None
        ) = None,
        json_body: (
            dict[str, Any] | None
        ) = None,
    ) -> dict[str, Any]:
        url = (
            f"{self.base_url}/"
            f"{endpoint.lstrip('/')}"
        )

        try:
            response = (
                self.session.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                    timeout=(
                        API_TIMEOUT_SECONDS
                    ),
                )
            )

        except requests.Timeout as exc:
            raise TrackingAPIError(
                "The tracking request "
                "timed out."
            ) from exc

        except (
            requests.RequestException
        ) as exc:
            raise TrackingAPIError(
                "Unable to connect to "
                "the tracking service."
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise TrackingAPIError(
                "The tracking service "
                "returned an invalid "
                "response.",
                response.status_code,
            ) from exc

        if not response.ok:
            if isinstance(data, dict):
                message = data.get(
                    "message",
                    "Unknown tracking error",
                )
            else:
                message = (
                    "Unknown tracking error"
                )

            raise TrackingAPIError(
                f"Tracking request "
                f"failed: {message}",
                response.status_code,
                data,
            )

        if not isinstance(data, dict):
            raise TrackingAPIError(
                "The tracking service "
                "returned an unexpected "
                "response.",
                response.status_code,
                data,
            )

        return data

    def list_all_shipments(
        self,
    ) -> list[dict[str, Any]]:
        shipments: list[
            dict[str, Any]
        ] = []

        skip = 0

        while True:
            data = self._request(
                "GET",
                "/ocean/shipments",
                params={
                    "skip": skip,
                    "take": (
                        LIST_PAGE_SIZE
                    ),
                },
            )

            batch = data.get(
                "shipments",
                [],
            )

            if not isinstance(
                batch,
                list,
            ):
                raise TrackingAPIError(
                    "Invalid shipment "
                    "list response."
                )

            shipments.extend(
                item
                for item in batch
                if isinstance(
                    item,
                    dict,
                )
            )

            meta = (
                data.get("meta", {})
                or {}
            )

            if (
                not meta.get("more")
                or not batch
            ):
                break

            skip += len(batch)

        return shipments

    def get_details(
        self,
        shipment_id: int,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            (
                "/ocean/shipments/"
                f"{shipment_id}"
            ),
        )

    def create_shipment(
        self,
        bl_number: str,
        carrier_scac: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/ocean/shipments",
            json_body={
                "booking_number": (
                    normalize_number(
                        bl_number
                    )
                ),
                "carrier": (
                    normalize_number(
                        carrier_scac
                    )
                ),
            },
        )

    @staticmethod
    def build_index(
        shipments: list[
            dict[str, Any]
        ],
    ) -> dict[
        str,
        dict[str, Any],
    ]:
        shipment_index: dict[
            str,
            dict[str, Any],
        ] = {}

        for shipment in shipments:
            for value in (
                shipment.get(
                    "booking_number"
                ),
                shipment.get(
                    "container_number"
                ),
            ):
                normalized = (
                    normalize_number(
                        value
                    )
                )

                if normalized:
                    shipment_index[
                        normalized
                    ] = shipment

        return shipment_index

    def analyze(
        self,
        entries: list[
            dict[str, str]
        ],
    ) -> list[
        dict[str, str]
    ]:
        shipment_index = (
            self.build_index(
                self.list_all_shipments()
            )
        )

        rows: list[
            dict[str, str]
        ] = []

        for entry in entries:
            bl_number = (
                normalize_number(
                    entry.get(
                        "bl_number"
                    )
                )
            )

            carrier_code = (
                normalize_number(
                    entry.get(
                        "carrier_scac"
                    )
                )
                or detect_carrier_scac(
                    bl_number
                )
            )

            summary = (
                shipment_index.get(
                    bl_number
                )
            )

            if summary:
                carrier = (
                    summary.get(
                        "carrier",
                        {},
                    )
                    or {}
                )

                if isinstance(
                    carrier,
                    dict,
                ):
                    carrier_code = str(
                        carrier.get(
                            "scac",
                            carrier_code,
                        )
                    )

                availability = (
                    "AVAILABLE"
                )

            else:
                availability = "NEW"

            rows.append(
                {
                    "B/L Number": (
                        bl_number
                    ),
                    "Carrier Code": (
                        carrier_code
                    ),
                    "Availability": (
                        availability
                    ),
                }
            )

        return rows

    @staticmethod
    def _created_id(
        data: dict[str, Any],
    ) -> int | None:
        shipment = (
            data.get(
                "shipment",
                {},
            )
            if isinstance(
                data.get("shipment"),
                dict,
            )
            else {}
        )

        nested_data = (
            data.get(
                "data",
                {},
            )
            if isinstance(
                data.get("data"),
                dict,
            )
            else {}
        )

        for value in (
            data.get("id"),
            data.get(
                "shipment_id"
            ),
            shipment.get("id"),
            nested_data.get("id"),
        ):
            try:
                if value is not None:
                    return int(value)

            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    @staticmethod
    def _latest_actual(
        shipment: dict[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        movements: list[
            dict[str, Any]
        ] = []

        containers = (
            shipment.get(
                "containers",
                [],
            )
            or []
        )

        for container in containers:
            if not isinstance(
                container,
                dict,
            ):
                continue

            container_movements = (
                container.get(
                    "movements",
                    [],
                )
                or []
            )

            for movement in (
                container_movements
            ):
                if not isinstance(
                    movement,
                    dict,
                ):
                    continue

                movement_status = str(
                    movement.get(
                        "status",
                        "",
                    )
                ).upper()

                if (
                    movement_status
                    == "ACT"
                ):
                    movements.append(
                        movement
                    )

        if not movements:
            return {}

        def movement_time(
            movement: dict[
                str,
                Any,
            ],
        ) -> datetime:
            parsed = parse_iso(
                movement.get(
                    "timestamp"
                )
            )

            if parsed is not None:
                return parsed

            return (
                datetime.min.replace(
                    tzinfo=timezone.utc
                )
            )

        return max(
            movements,
            key=movement_time,
        )

    @staticmethod
    def _blank_row(
        bl_number: str,
        status: str,
        remarks: str,
    ) -> dict[str, Any]:
        return {
            "B/L Number": (
                bl_number
            ),
            "Status": status,
            "Carrier": "N/A",
            "SCAC": "N/A",
            "Container Number(s)": (
                "N/A"
            ),
            "Container Count": (
                "N/A"
            ),
            "POL": "N/A",
            "POL Country Code": (
                "N/A"
            ),
            "ETD": "N/A",
            "POD": "N/A",
            "POD Country Code": (
                "N/A"
            ),
            "ETA": "N/A",
            "Initial ETA": "N/A",
            "ETA Change (Days)": (
                "N/A"
            ),
            "Vessel": "N/A",
            "Voyage": "N/A",
            "Latest Event": "N/A",
            "Latest Place": "N/A",
            "Latest Event Time": (
                "N/A"
            ),
            "Transshipment Count": (
                "N/A"
            ),
            "Last Checked": "N/A",
            "Remarks": remarks,
        }

    @staticmethod
    def _shipment_from_response(
        data: dict[str, Any],
    ) -> dict[str, Any]:
        shipment = data.get(
            "shipment"
        )

        if isinstance(
            shipment,
            dict,
        ):
            return shipment

        return data

    def _parse(
        self,
        requested_bl: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        shipment = (
            self._shipment_from_response(
                data
            )
        )

        route = (
            shipment.get(
                "route",
                {},
            )
            or {}
        )

        pol = (
            route.get(
                "port_of_loading",
                {},
            )
            or {}
        )

        pod = (
            route.get(
                "port_of_discharge",
                {},
            )
            or {}
        )

        pol_location = (
            pol.get(
                "location",
                {},
            )
            if isinstance(
                pol,
                dict,
            )
            else {}
        ) or {}

        pod_location = (
            pod.get(
                "location",
                {},
            )
            if isinstance(
                pod,
                dict,
            )
            else {}
        ) or {}

        carrier = (
            shipment.get(
                "carrier",
                {},
            )
            or {}
        )

        containers = (
            shipment.get(
                "containers",
                [],
            )
            or []
        )

        latest = (
            self._latest_actual(
                shipment
            )
        )

        latest_location = (
            latest.get(
                "location",
                {},
            )
            or {}
        )

        vessel = (
            latest.get(
                "vessel",
                {},
            )
            or {}
        )

        current_eta = (
            pod.get(
                "date_of_discharge"
            )
            or pod.get("eta")
            or pod.get(
                "estimated_arrival"
            )
        )

        initial_eta = (
            pod.get(
                "date_of_discharge_initial"
            )
            or pod.get(
                "initial_eta"
            )
            or pod.get(
                "initialEta"
            )
        )

        container_numbers = [
            str(
                container.get(
                    "number"
                )
            )
            for container in (
                containers
            )
            if isinstance(
                container,
                dict,
            )
            and container.get(
                "number"
            )
        ]

        event_code = str(
            latest.get(
                "event",
                "",
            )
        ).upper()

        return {
            "B/L Number": (
                shipment.get(
                    "booking_number"
                )
                or shipment.get(
                    "bl_number"
                )
                or requested_bl
            ),
            "Status": (
                shipment.get(
                    "status",
                    "INPROGRESS",
                )
            ),
            "Carrier": (
                carrier.get(
                    "name",
                    "N/A",
                )
                if isinstance(
                    carrier,
                    dict,
                )
                else str(carrier)
            ),
            "SCAC": (
                carrier.get(
                    "scac",
                    "N/A",
                )
                if isinstance(
                    carrier,
                    dict,
                )
                else "N/A"
            ),
            "Container Number(s)": (
                ", ".join(
                    container_numbers
                )
                or shipment.get(
                    "container_number",
                    "N/A",
                )
            ),
            "Container Count": (
                shipment.get(
                    "container_count",
                    len(
                        container_numbers
                    ),
                )
            ),
            "POL": (
                extract_location_name(
                    pol
                )
            ),
            "POL Country Code": (
                extract_country_code(
                    pol_location,
                    pol,
                )
            ),
            "ETD": format_datetime(
                pol.get(
                    "date_of_loading"
                )
                or pol.get("etd")
                or pol.get(
                    "estimated_departure"
                )
            ),
            "POD": (
                extract_location_name(
                    pod
                )
            ),
            "POD Country Code": (
                extract_country_code(
                    pod_location,
                    pod,
                )
            ),
            "ETA": (
                format_datetime(
                    current_eta
                )
            ),
            "Initial ETA": (
                format_datetime(
                    initial_eta
                )
            ),
            "ETA Change (Days)": (
                calculate_eta_change(
                    current_eta,
                    initial_eta,
                )
            ),
            "Vessel": (
                vessel.get(
                    "name",
                    "N/A",
                )
                if isinstance(
                    vessel,
                    dict,
                )
                else "N/A"
            ),
            "Voyage": (
                latest.get(
                    "voyage",
                    "N/A",
                )
            ),
            "Latest Event": (
                EVENT_LABELS.get(
                    event_code,
                    event_code or "N/A",
                )
            ),
            "Latest Place": (
                latest_location.get(
                    "name",
                    "N/A",
                )
                if isinstance(
                    latest_location,
                    dict,
                )
                else "N/A"
            ),
            "Latest Event Time": (
                format_datetime(
                    latest.get(
                        "timestamp"
                    )
                )
            ),
            "Transshipment Count": (
                route.get(
                    "ts_count",
                    route.get(
                        "transshipment_count",
                        "N/A",
                    ),
                )
            ),
            "Last Checked": (
                format_datetime(
                    shipment.get(
                        "checked_at"
                    )
                    or shipment.get(
                        "last_checked"
                    )
                    or shipment.get(
                        "lastChecked"
                    )
                )
            ),
            "Remarks": (
                "Tracking data "
                "retrieved."
                if route
                else
                "Tracking data is "
                "being processed."
            ),
        }

    def track(
        self,
        entries: list[
            dict[str, str]
        ],
        register_missing: bool,
        progress_callback: (
            ProgressCallback | None
        ) = None,
    ) -> tuple[
        list[dict[str, Any]],
        dict[str, Any],
    ]:
        shipment_index = (
            self.build_index(
                self.list_all_shipments()
            )
        )

        rows: list[
            dict[str, Any]
        ] = []

        raw_responses: dict[
            str,
            Any,
        ] = {}

        total = len(entries)

        for current, entry in enumerate(
            entries,
            start=1,
        ):
            bl_number = (
                normalize_number(
                    entry.get(
                        "bl_number"
                    )
                )
            )

            carrier_code = (
                normalize_number(
                    entry.get(
                        "carrier_scac"
                    )
                )
                or detect_carrier_scac(
                    bl_number
                )
            )

            summary = (
                shipment_index.get(
                    bl_number
                )
            )

            try:
                if summary:
                    details = (
                        self.get_details(
                            int(
                                summary[
                                    "id"
                                ]
                            )
                        )
                    )

                    row = self._parse(
                        bl_number,
                        details,
                    )

                    raw_responses[
                        bl_number
                    ] = details

                elif not register_missing:
                    row = self._blank_row(
                        bl_number,
                        "NOT REGISTERED",
                        "Registration is "
                        "required before "
                        "tracking.",
                    )

                    raw_responses[
                        bl_number
                    ] = {
                        "message": (
                            "Registration "
                            "was not "
                            "requested."
                        )
                    }

                elif not carrier_code:
                    row = self._blank_row(
                        bl_number,
                        "CARRIER REQUIRED",
                        "A valid carrier "
                        "code is required.",
                    )

                    raw_responses[
                        bl_number
                    ] = {
                        "message": (
                            "Carrier code "
                            "is required."
                        )
                    }

                else:
                    created = (
                        self.create_shipment(
                            bl_number,
                            carrier_code,
                        )
                    )

                    shipment_id = (
                        self._created_id(
                            created
                        )
                    )

                    if shipment_id is None:
                        refreshed = (
                            self.build_index(
                                self.list_all_shipments()
                            ).get(
                                bl_number
                            )
                        )

                        if (
                            refreshed
                            and refreshed.get(
                                "id"
                            )
                        ):
                            shipment_id = int(
                                refreshed[
                                    "id"
                                ]
                            )

                    if shipment_id is None:
                        row = self._blank_row(
                            bl_number,
                            "PROCESSING",
                            "Registration "
                            "completed. "
                            "Tracking data "
                            "is being "
                            "processed.",
                        )

                        raw_responses[
                            bl_number
                        ] = created

                    else:
                        try:
                            details = (
                                self.get_details(
                                    shipment_id
                                )
                            )

                            row = self._parse(
                                bl_number,
                                details,
                            )

                            raw_responses[
                                bl_number
                            ] = {
                                "create_response": (
                                    created
                                ),
                                "details_response": (
                                    details
                                ),
                            }

                        except (
                            TrackingAPIError
                        ) as exc:
                            row = (
                                self._blank_row(
                                    bl_number,
                                    "PROCESSING",
                                    "Registration "
                                    "completed. "
                                    "Tracking "
                                    "data is "
                                    "being "
                                    "processed.",
                                )
                            )

                            raw_responses[
                                bl_number
                            ] = {
                                "create_response": (
                                    created
                                ),
                                "detail_error": (
                                    str(exc)
                                ),
                            }

            except (
                TrackingAPIError
            ) as exc:
                row = self._blank_row(
                    bl_number,
                    "ERROR",
                    "Unable to retrieve "
                    "tracking data.",
                )

                raw_responses[
                    bl_number
                ] = {
                    "error": str(exc),
                    "status_code": (
                        exc.status_code
                    ),
                    "payload": (
                        exc.payload
                    ),
                }

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                row = self._blank_row(
                    bl_number,
                    "ERROR",
                    "Unable to process "
                    "the tracking "
                    "response.",
                )

                raw_responses[
                    bl_number
                ] = {
                    "error": str(exc)
                }

            rows.append(row)

            if progress_callback:
                progress_callback(
                    current,
                    total,
                    bl_number,
                )

        return rows, raw_responses


ShipsGoProvider = OceanTrackingProvider
ShipsGoAPIError = TrackingAPIError