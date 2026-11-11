import json
import threading
import time
from copy import deepcopy

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ...analytics import Analytics
from ..disclosure import protect_metric
from ..security import current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class AggregateCache:
    def __init__(self, settings):
        self.settings = settings
        self.entries = {}
        self.inflight = {}
        self.lock = threading.Lock()

    def token(self):
        paths = [self.settings.census_db]
        for folder in ("app/config/analytics", "app/sql/analytics"):
            paths.extend(sorted(p for p in (self.settings.root / folder).rglob("*") if p.is_file()))
        return (
            self.settings.minimum_contributors,
            tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in paths),
        )

    def get(self, key, build):
        if self.settings.aggregate_cache_seconds == 0:
            return build()
        token = self.token()
        while True:
            with self.lock:
                item = self.entries.get(key)
                if (
                    item
                    and item[0] == token
                    and time.monotonic() - item[1] < self.settings.aggregate_cache_seconds
                ):
                    return deepcopy(item[2])
                event = self.inflight.get((key, token))
                if event is None:
                    event = threading.Event()
                    self.inflight[(key, token)] = event
                    break
            event.wait()
        try:
            result = build()
            with self.lock:
                if len(self.entries) >= 128:
                    oldest = min(self.entries, key=lambda k: self.entries[k][1])
                    del self.entries[oldest]
                self.entries[key] = (token, time.monotonic(), result)
            return deepcopy(result)
        finally:
            with self.lock:
                self.inflight.pop((key, token), None)
                event.set()


class MetricRequest(BaseModel):
    metric_id: str = Field(max_length=100)
    group_by: list[str] = Field(default_factory=list, max_length=3)
    filters: dict[str, str | list[str]] = Field(default_factory=dict)
    location: str = "assignment"


@router.get("/business-summary")
def business_summary(
    request: Request,
    kecamatan: str = Query(default="", max_length=40),
    desa: str = Query(default="", max_length=40),
    sls: str = Query(default="", max_length=40),
    subsls: str = Query(default="", max_length=40),
    user=Depends(current_user),
):
    filters = {k: v for k, v in dict(kecamatan=kecamatan, desa=desa, sls=sls, subsls=subsls).items() if v}

    def build():
        with Analytics(request.app.state.settings.census_db, request.app.state.settings.root) as api:
            counts = {
                key: protect_metric(
                    api.query(key, filters=filters), request.app.state.settings.minimum_contributors
                )["rows"]
                for key in (
                    "usaha.enumerated_family_count",
                    "usaha.enumerated_bku_count",
                    "ub.enumerated_count",
                )
            }
        return {"counts": counts, "filters": filters, "systems_not_added_together": True}

    return request.app.state.aggregate_cache.get(("business-summary", tuple(sorted(filters.items()))), build)


@router.get("/summary")
def summary(
    request: Request,
    kecamatan: str = Query(default="", max_length=40),
    desa: str = Query(default="", max_length=40),
    sls: str = Query(default="", max_length=40),
    subsls: str = Query(default="", max_length=40),
    user=Depends(current_user),
):
    filters = {k: v for k, v in dict(kecamatan=kecamatan, desa=desa, sls=sls, subsls=subsls).items() if v}

    def build():
        minimum = request.app.state.settings.minimum_contributors
        with Analytics(request.app.state.settings.census_db, request.app.state.settings.root) as api:
            counts = [
                (key, protect_metric(api.query(key, filters=filters), minimum)["rows"])
                for key in [
                    "assignment_tgr.count",
                    "assignment_ub.count",
                    "keluarga.count",
                    "anggota.count",
                    "bku.count",
                    "bku.business_enumerated_count",
                    "usaha.count",
                    "ub.count",
                    "usaha.enumerated_count",
                    "usaha.enumerated_family_count",
                    "usaha.enumerated_residential_count",
                    "usaha.enumerated_mixed_count",
                    "usaha.enumerated_bku_count",
                    "usaha.enumerated_unclassified_count",
                    "ub.enumerated_count",
                    "usaha.qualified_count",
                    "usaha.qualified_family_count",
                    "usaha.qualified_bku_count",
                    "usaha.review_count",
                    "ub.qualified_count",
                ]
            ]
            extras = [
                protect_metric(api.query(key, filters=filters), minimum)
                for key in [
                    "usaha.internet_yes_rate",
                    "ub.internet_yes_rate",
                    "usaha.workers_total_valid",
                    "ub.workers_total_valid",
                    "ub.complete_module_coverage",
                ]
            ]
            region = protect_metric(
                api.query("assignment_tgr.count", filters=filters, group_by="kecamatan"), minimum
            )
        return dict(
            counts=dict(counts),
            indicators=extras,
            region=region,
            baseline="Snapshot lokal aktif",
            filters=filters,
            systems_not_added_together=True,
            sensitivity="INTERNAL_AGGREGATE",
            suppression_note=f"Kebijakan lokal k={minimum}; bukan standar resmi. Query tumpang tindih tetap membutuhkan pembatasan akses.",
        )

    return request.app.state.aggregate_cache.get(("summary", tuple(sorted(filters.items()))), build)


@router.post("/query")
def metric(payload: MetricRequest, request: Request, user=Depends(current_user)):
    # The established public semantic API enforces metric/dimension whitelists,
    # bound values, exact grains and disclosure control.
    def build():
        with Analytics(request.app.state.settings.census_db, request.app.state.settings.root) as api:
            return protect_metric(
                api.query(payload.metric_id, payload.filters, payload.group_by, payload.location),
                request.app.state.settings.minimum_contributors,
            )

    key = ("metric", json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":")))
    return request.app.state.aggregate_cache.get(key, build)


@router.get("/metrics")
def metrics(request: Request, user=Depends(current_user)):
    from ...analytics.registry import Registry

    registry = Registry(request.app.state.settings.root)
    return dict(
        rows=[
            {
                k: m[k]
                for k in [
                    "metric_id",
                    "name",
                    "domain",
                    "grain",
                    "unit",
                    "period",
                    "dimensions",
                    "interpretation_limits",
                ]
            }
            for m in registry.metrics.values()
        ]
    )
