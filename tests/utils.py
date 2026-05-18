"""Utility functions for harmony-autotester pytest test suites."""

from datetime import datetime


def get_bounding_box(granule):
    """Extract the bounding box from a granule UMM JSON response.

    Notes:
        Adopted from l2ss-py-autotest:
        https://github.com/podaac/l2ss-py-autotest/blob/9243876/tests/verify_collection.py#L246
    """
    try:
        longitude_list = []
        latitude_list = []
        spatial_extent = granule['umm']['SpatialExtent']
        geometry = spatial_extent['HorizontalSpatialDomain']['Geometry']

        polygons = geometry.get('GPolygons')
        lines = geometry.get('Lines')
        if polygons:
            for polygon in polygons:
                points = polygon['Boundary']['Points']
                for point in points:
                    longitude_list.append(point.get('Longitude'))
                    latitude_list.append(point.get('Latitude'))
                break
        elif lines:
            points = lines[0].get('Points')
            for point in points:
                longitude_list.append(point.get('Longitude'))
                latitude_list.append(point.get('Latitude'))

        if not longitude_list or not latitude_list:  # Check if either list is empty
            raise ValueError('Empty longitude or latitude list')

        north = max(latitude_list)
        south = min(latitude_list)
        west = min(longitude_list)
        east = max(longitude_list)

    except (KeyError, ValueError):
        bounding_box = geometry['BoundingRectangles'][0]

        north = bounding_box.get('NorthBoundingCoordinate')
        south = bounding_box.get('SouthBoundingCoordinate')
        west = bounding_box.get('WestBoundingCoordinate')
        east = bounding_box.get('EastBoundingCoordinate')

    return west, east, south, north


def generate_near_full_spatial_box(granules):
    """Return the near-full bounding box for spatial subsetting tests.

    Reduce each granule bounding box by 5% on every side
    to avoid exact edge alignment
    then use the min/max extents of all reduced granules
    to create a combined near-full spatial subset box.

    """
    boxes = [get_bounding_box(granule) for granule in granules]

    interior_boxes = [
        (
            west + (east - west) * 0.05,
            west + (east - west) * 0.95,
            south + (north - south) * 0.05,
            south + (north - south) * 0.95,
        )
        for west, east, south, north in boxes
    ]

    west = max(box[0] for box in interior_boxes)
    east = min(box[1] for box in interior_boxes)
    south = max(box[2] for box in interior_boxes)
    north = min(box[3] for box in interior_boxes)

    return west, east, south, north


def get_temporal_range(granule):
    """Extract the temporal range from a granule UMM JSON response."""
    start_time = granule['umm']['TemporalExtent']['RangeDateTime']['BeginningDateTime']
    end_time = granule['umm']['TemporalExtent']['RangeDateTime']['EndingDateTime']
    return start_time, end_time


def generate_near_full_temporal_range(granules):
    """Return the near-full temporal range for temporal subsetting tests."""
    umm_times = [get_temporal_range(granule) for granule in granules]

    obj_times = [
        (datetime.fromisoformat(start_time), datetime.fromisoformat(end_time))
        for start_time, end_time in umm_times
    ]

    reduced_times = [
        (
            start_time + (end_time - start_time) * 0.05,
            start_time + (end_time - start_time) * 0.95,
        )
        for start_time, end_time in obj_times
    ]
    start_time = min(start_time for start_time, end_time in reduced_times)
    end_time = max(end_time for start_time, end_time in reduced_times)

    return start_time, end_time
