from common.db import query_object


def get_parcel_from_voronoi(connection, logger, geographic_point_wkt):
    logger.info("getting voronoi from database")
    sql = "select verisk3Dvi_get_parcel_from_voronoi(ST_GeomFromText(%(geographic_point_wkt)s,4326))"
    args = {"geographic_point_wkt": geographic_point_wkt}
    return query_object(connection, logger, sql, args)

