"""Safe, non-persistent client for the documented Work24 job-list XML API."""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Callable

WORK24_LIST_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
FILTERS = frozenset({
    "region", "occupation", "salTp", "minPay", "maxPay", "education", "career",
    "minCareerM", "maxCareerM", "pref", "subway", "empTp", "termContractMmcnt",
    "holidayTp", "coTp", "busino", "dtlSmlgntYn", "workStudyJoinYn",
    "smlgntCoClcd", "workerCnt", "welfare", "certLic", "regDate",
    "untilEmpWantedYn", "minWantedAuthDt", "maxWantedAuthDt", "empTpGb",
    "sortOrderBy", "major", "foreignLanguage", "comPreferential",
    "pfPreferential", "workHrCd", "keyword",
})
JOB_FIELDS = (
    "wantedAuthNo", "company", "busino", "indTpNm", "title", "salTpNm", "sal",
    "minSal", "maxSal", "region", "holidayTpNm", "minEdubg", "maxEdubg",
    "career", "regDt", "closeDt", "infoSvc", "wantedInfoUrl",
    "wantedMobileInfoUrl", "zipCd", "strtnmCd", "basicAddr", "detailAddr",
    "empTpCd", "jobsCd", "smodifyDtm",
)


class Work24ApiError(RuntimeError):
    """Sanitized provider/transport error; never includes URL or credentials."""


@dataclass(frozen=True)
class Work24JobList:
    total: int
    start_page: int
    display: int
    jobs: tuple[dict[str, str], ...]


class Work24Client:
    """One-page list client; importing or constructing it does not make a request."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 10.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        key = api_key.strip() if isinstance(api_key, str) else ""
        if not key:
            raise ValueError("Work24 API key is required")
        if not 0 < timeout <= 60:
            raise ValueError("timeout must be greater than 0 and at most 60 seconds")
        self._api_key = key
        self._timeout = timeout
        self._opener = opener or urllib.request.urlopen

    @classmethod
    def from_environment(cls, **kwargs: Any) -> "Work24Client":
        """Read WORK24_API_KEY from the process environment (does not load .env)."""
        key = os.environ.get("WORK24_API_KEY", "")
        if not key:
            raise ValueError("WORK24_API_KEY is not set in the process environment")
        return cls(key, **kwargs)

    def list_jobs(
        self,
        *,
        start_page: int = 1,
        display: int = 10,
        filters: dict[str, str] | None = None,
    ) -> Work24JobList:
        if isinstance(start_page, bool) or not isinstance(start_page, int) or not 1 <= start_page <= 1000:
            raise ValueError("start_page must be an integer from 1 to 1000")
        if isinstance(display, bool) or not isinstance(display, int) or not 1 <= display <= 100:
            raise ValueError("display must be an integer from 1 to 100")
        params = self._validated_filters(filters if filters is not None else {})
        params.update({
            "authKey": self._api_key,
            "callTp": "L",
            "returnType": "XML",
            "startPage": str(start_page),
            "display": str(display),
        })
        url = WORK24_LIST_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"Accept": "application/xml, text/xml"})
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise Work24ApiError("Work24 returned an unsuccessful HTTP status")
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except Work24ApiError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Work24ApiError("Work24 request failed; URL and credentials were omitted") from None
        if len(body) > MAX_RESPONSE_BYTES:
            raise Work24ApiError("Work24 response exceeded the configured size limit")
        return self._parse_xml(body)

    @staticmethod
    def _validated_filters(filters: dict[str, str]) -> dict[str, str]:
        if not isinstance(filters, dict):
            raise ValueError("filters must be a dictionary")
        unknown = set(filters) - FILTERS
        if unknown:
            raise ValueError("unsupported Work24 filter name")
        result: dict[str, str] = {}
        for name, value in filters.items():
            if not isinstance(value, str):
                raise ValueError(f"filter {name} must be text")
            cleaned = value.strip()
            if len(cleaned) > 2000:
                raise ValueError(f"filter {name} is too long")
            if cleaned:
                result[name] = cleaned
        if "salTp" in result and not {"minPay", "maxPay"}.issubset(result):
            raise ValueError("minPay and maxPay are required when salTp is specified")
        if ({"minPay", "maxPay"} & result.keys()) and "salTp" not in result:
            raise ValueError("salTp is required when minPay or maxPay is specified")
        career_fields = {"minCareerM", "maxCareerM"}
        if "career" in result and not career_fields.issubset(result):
            raise ValueError("minCareerM and maxCareerM are required when career is specified")
        if (career_fields & result.keys()) and "career" not in result:
            raise ValueError("career is required when career-month filters are specified")
        return result

    @staticmethod
    def _parse_xml(body: bytes) -> Work24JobList:
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            raise Work24ApiError("Work24 response was not valid XML") from None

        def child_text(element: ET.Element, name: str) -> str:
            for child in element:
                if child.tag.rsplit("}", 1)[-1] == name:
                    return (child.text or "").strip()
            return ""

        error_text = child_text(root, "error") or child_text(root, "message") or child_text(root, "errMsg")
        message_cd = child_text(root, "messageCd")
        if error_text or message_cd:
            raise Work24ApiError(f"Work24 API 응답 메시지 ({message_cd or 'ERROR'}): {error_text}")

        total_text = child_text(root, "total")
        start_text = child_text(root, "startPage")
        display_text = child_text(root, "display")
        if not total_text or not start_text or not display_text:
            raise Work24ApiError("Work24 response did not match the documented job-list XML schema")
        try:
            total, start_page, display = int(total_text), int(start_text), int(display_text)
        except ValueError:
            raise Work24ApiError("Work24 response contained invalid paging values") from None
        wanted_nodes = [
            child for child in root
            if child.tag.rsplit("}", 1)[-1] == "wanted"
        ]
        jobs = tuple(
            {field: child_text(node, field) for field in JOB_FIELDS}
            for node in wanted_nodes
        )
        return Work24JobList(total=total, start_page=start_page, display=display, jobs=jobs)
