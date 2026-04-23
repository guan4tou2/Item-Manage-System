from app.schemas.stats import (
    OverviewStats,
    CategoryBucket,
    LocationBucket,
    TagBucket,
)


def test_overview_stats_serializes_all_fields():
    s = OverviewStats(
        total_items=5,
        total_quantity=10,
        total_categories=2,
        total_locations=1,
        total_tags=3,
    )
    assert s.model_dump() == {
        "total_items": 5,
        "total_quantity": 10,
        "total_categories": 2,
        "total_locations": 1,
        "total_tags": 3,
        "total_warehouses": 0,
        "low_stock_items": 0,
        "active_loans": 0,
    }


def test_category_bucket_allows_null_id_and_name():
    b = CategoryBucket(category_id=None, name=None, count=7)
    assert b.model_dump() == {"category_id": None, "name": None, "count": 7}


def test_location_bucket_allows_null_id_and_label():
    b = LocationBucket(location_id=None, label=None, count=4)
    assert b.model_dump() == {"location_id": None, "label": None, "count": 4}


def test_tag_bucket_requires_id_and_name():
    b = TagBucket(tag_id=1, name="red", count=2)
    assert b.model_dump() == {"tag_id": 1, "name": "red", "count": 2}
