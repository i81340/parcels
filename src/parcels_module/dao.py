from common.db import query_all_RealDictCursor


def get_parcels_by_geometry(connection, logger, wkt, buffer):
    if buffer is not None:
        sql = "SELECT ST_AsGeoJSON((st_buffer(parcel.geom, %(buffer)s)))::jsonb as geometry"
    else:
        sql = "SELECT ST_AsGeoJSON(parcel.geom)::jsonb as geometry"

    sql = sql + ",  ST_Area(parcel.geom::geography) as area, parcel.id as id, parcel.parcel_number as apn, " \
                "state.code || county.code as fips, " \
                "state.name as state," \
                "county.name as county, " \
                "parcel.raw_street_address as \"siteAddress\", " \
                "parcel.zip as zip, " \
                "city.name as city, " \
                "parcel.acreage ||'' as \"calculatedAcres\", " \
                "parcel.updated as updated, " \
                "parcel.soruce_reliability as \"sourceReliability\" " \
                "FROM parcel " \
                "LEFT JOIN city ON (parcel.city_id = city.id) " \
                "LEFT JOIN data_source ON (parcel.data_source_id = data_source.id) " \
                "LEFT JOIN state ON (data_source.state_id = state.id) " \
                "LEFT JOIN county ON (data_source.county_id = county.id) " \
                "WHERE ( parcel.geom && ST_GeomFromText(%(wkt)s, 4326) " \
                "AND ST_Intersects(parcel.geom, ST_GeomFromText(%(wkt)s, 4326)) ) "

    args = {'wkt': wkt, 'buffer': buffer}
    logger.info(args)
    logger.info(sql)
    return query_all_RealDictCursor(connection, logger, sql, args)


