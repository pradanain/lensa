import json
import threading
import time
from copy import deepcopy

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ...analytics import Analytics
from ...analytics.snapshot import snapshot_token
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
        return (self.settings.minimum_contributors,
                snapshot_token(self.settings.census_db, self.settings.root))

    def get(self, key, build, token=None):
        if self.settings.aggregate_cache_seconds == 0:
            return build()
        token = self.token() if token is None else token
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


def cached_metric(request, metric_id, filters=None, group_by=None, location="assignment", api=None):
    payload = MetricRequest(metric_id=metric_id, filters=filters or {}, group_by=group_by or [], location=location)

    def build():
        def query(client):
            return protect_metric(client.query(metric_id, payload.filters, payload.group_by, location),
                                  request.app.state.settings.minimum_contributors)
        if api is not None:
            return query(api)
        settings = request.app.state.settings
        with Analytics(settings.census_db, settings.root) as client:
            return query(client)

    key = ("metric", json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":")))
    if api is not None and not api._cacheable:
        return build()
    # An existing SQLite read transaction can outlive a file update. Its result
    # belongs to that transaction's generation, never the newer on-disk token.
    token = (request.app.state.settings.minimum_contributors, api._snapshot) if api is not None else None
    return request.app.state.aggregate_cache.get(key, build, token=token)


def warm_common_metrics(app):
    """Prepare public, suppressed landing-page results before accepting traffic."""
    settings = app.state.settings
    request = Request({"type": "http", "app": app})
    with Analytics(settings.census_db, settings.root) as api:
        for key in ("usaha.enumerated_family_count", "usaha.enumerated_bku_count", "ub.enumerated_count",
                    "keluarga.count", "anggota.count", "usaha.internet_yes_rate", "ub.internet_yes_rate"):
            cached_metric(request, key, api=api)


@router.get("/dashboard")
def dashboard(
    request: Request,
    part: str = Query(default="counts", pattern="^(counts|internet|notes)$"),
    kecamatan: str = Query(default="", max_length=40),
    desa: str = Query(default="", max_length=40),
    sls: str = Query(default="", max_length=40),
    subsls: str = Query(default="", max_length=40),
    user=Depends(current_user),
):
    filters = {k: v for k, v in dict(kecamatan=kecamatan, desa=desa, sls=sls, subsls=subsls).items() if v}
    metrics = {
        "counts": ("usaha.enumerated_family_count", "usaha.enumerated_bku_count", "ub.enumerated_count",
                   "keluarga.count", "anggota.count"),
        "internet": ("usaha.internet_yes_rate", "ub.internet_yes_rate"),
        "notes": ("assignment_tgr.count", "assignment_ub.count", "bku.count", "usaha.enumerated_count"),
    }[part]
    settings = request.app.state.settings
    with Analytics(settings.census_db, settings.root) as api:
        results = [cached_metric(request, key, filters, api=api) for key in metrics]
    return dict(counts={item["metric_id"]: item["rows"] for item in results} if part != "internet" else {},
                indicators=results if part == "internet" else [], filters=filters)


@router.get("/business-summary")
def business_summary(
    request: Request,
    kecamatan: str = Query(default="", max_length=40),
    desa: str = Query(default="", max_length=40),
    sls: str = Query(default="", max_length=40),
    subsls: str = Query(default="", max_length=40),
    turnover_group: str = Query(default="", pattern=r"^(MIKRO|KECIL|MENENGAH|BESAR|UNAVAILABLE|REVIEW)?$"),
    turnover_basis: str = Query(default="", pattern=r"^(REPORTED_ANNUAL|ESTIMATE_MONTHLY_X12|UNAVAILABLE)?$"),
    user=Depends(current_user),
):
    filters = {k: v for k, v in dict(kecamatan=kecamatan, desa=desa, sls=sls, subsls=subsls,
        turnover_group=turnover_group, turnover_basis=turnover_basis).items() if v}

    def build():
        with Analytics(request.app.state.settings.census_db, request.app.state.settings.root) as api:
            counts = {
                key: cached_metric(request, key, filters, api=api)["rows"]
                for key in (
                    "usaha.enumerated_family_count",
                    "usaha.enumerated_bku_count",
                    "ub.enumerated_count",
                )
            }
        return {"counts": counts, "filters": filters, "systems_not_added_together": True}

    return request.app.state.aggregate_cache.get(("business-summary", tuple(sorted(filters.items()))), build)


@router.get("/family-summary")
def family_summary(
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
                key: cached_metric(request, key, filters, api=api)["rows"]
                for key in ("keluarga.count", "anggota.count")
            }
        return {"counts": counts, "filters": filters, "grains_not_added_together": True}

    return request.app.state.aggregate_cache.get(("family-summary", tuple(sorted(filters.items()))), build)


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
                (key, cached_metric(request, key, filters, api=api)["rows"])
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
                cached_metric(request, key, filters, api=api)
                for key in [
                    "usaha.internet_yes_rate",
                    "ub.internet_yes_rate",
                    "usaha.workers_total_valid",
                    "ub.workers_total_valid",
                    "ub.complete_module_coverage",
                ]
            ]
            region = cached_metric(request, "assignment_tgr.count", filters, ["kecamatan"], api=api)
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
    return cached_metric(request, payload.metric_id, payload.filters, payload.group_by, payload.location)


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
