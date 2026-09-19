"""Read-only, public GitHub Contents API adapter at an exact immutable commit.

No API token, custom URL/host, redirect, private repository, credential or
permission escalation support. It is NOT an authenticated/private connector.
Use with the separately bounded acquisition handoff; results cannot prove
the human caller had permission to access any other repository or source.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from source_read_acquisition_handoff import FetchedSource

__all__ = ["PinnedPublicGitHubReader", "PublicReadError"]

_NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}\Z")
_PATH = re.compile(r"[A-Za-z0-9._/-]{1,256}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_BLOB = re.compile(r"[0-9a-f]{40}\Z")
MAX_CONTENT = 131_072
MAX_RESPONSE = 196_608


class PublicReadError(Exception):
    """Opaque, non-disclosing read/validation failure."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _path_ok(path: Any) -> bool:
    return (
        type(path) is str and _PATH.fullmatch(path) is not None
        and not path.startswith("/") and not path.endswith("/")
        and all(component not in ("", ".", "..") for component in path.split("/"))
    )


@dataclass(frozen=True)
class PinnedPublicGitHubReader:
    owner: str
    repository: str
    commit_sha: str
    allowed_paths: tuple[str, ...]
    _transport: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not str
            or _NAME.fullmatch(self.owner) is None
            or self.owner in (".", "..")
            or type(self.repository) is not str
            or _NAME.fullmatch(self.repository) is None
            or self.repository in (".", "..")
            or type(self.commit_sha) is not str
            or _COMMIT.fullmatch(self.commit_sha) is None
            or type(self.allowed_paths) is not tuple
            or not self.allowed_paths
            or any(not _path_ok(path) for path in self.allowed_paths)
            or len(set(self.allowed_paths)) != len(self.allowed_paths)
            or (self._transport is not None and not callable(self._transport))
        ):
            raise PublicReadError("invalid_public_reader_configuration")

    def __call__(self, source_id: str) -> FetchedSource:
        if type(source_id) is not str:
            raise PublicReadError("source_read_failed")
        prefix = "github:" + self.owner + "/" + self.repository + ":"
        if not source_id.startswith(prefix):
            raise PublicReadError("source_read_failed")
        path = source_id[len(prefix):]
        if path not in self.allowed_paths:
            raise PublicReadError("source_read_failed")

        url = (
            "https://api.github.com/repos/"
            + urllib.parse.quote(self.owner, safe="")
            + "/" + urllib.parse.quote(self.repository, safe="")
            + "/contents/" + urllib.parse.quote(path, safe="/")
            + "?ref=" + self.commit_sha
        )
        request = urllib.request.Request(
            url, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "bounded-public-source-read-reference",
            }, method="GET",
        )
        try:
            if self._transport is None:
                with urllib.request.build_opener(_NoRedirect()).open(
                    request, timeout=5
                ) as response:
                    if response.status != 200:
                        raise PublicReadError("source_read_failed")
                    body = response.read(MAX_RESPONSE + 1)
            else:
                with self._transport(request, timeout=5) as response:
                    if response.status != 200:
                        raise PublicReadError("source_read_failed")
                    body = response.read(MAX_RESPONSE + 1)

            if type(body) is not bytes or len(body) > MAX_RESPONSE:
                raise PublicReadError("source_read_failed")
            data = json.loads(body.decode("utf-8"))
            if type(data) is not dict:
                raise PublicReadError("source_read_failed")
            if (
                type(data.get("type")) is not str or data["type"] != "file"
                or type(data.get("encoding")) is not str
                or data["encoding"] != "base64"
                or type(data.get("content")) is not str
                or type(data.get("size")) is not int
                or not (0 <= data["size"] <= MAX_CONTENT)
                or type(data.get("sha")) is not str
                or _BLOB.fullmatch(data["sha"]) is None
                or type(data.get("path")) is not str
                or data["path"] != path
            ):
                raise PublicReadError("source_read_failed")
            raw = base64.b64decode(
                data["content"].replace("\n", ""), validate=True
            )
            if len(raw) != data["size"]:
                raise PublicReadError("source_read_failed")
            git_blob_sha = hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
            ).hexdigest()
            if git_blob_sha != data["sha"]:
                raise PublicReadError("source_read_failed")
        except Exception:
            # Do not leak HTTP error body, repository URL, request path,
            # request metadata, returned bytes or transport exception detail.
            raise PublicReadError("source_read_failed") from None

        return FetchedSource(
            source_id=source_id, source_version=self.commit_sha,
            raw_payload=raw,
        )
