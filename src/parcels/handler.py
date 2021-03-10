import time
import json
import logging
import psycopg2
import os
import requests
import xml.etree.ElementTree as ET
from parcels_module import dao
from blueprints_module import dao as blueprints_dao
from shapely.wkt import loads
from shapely.geometry import mapping
from common import db, secrets_manager, logging_formatter
from tokenizer import Tokenizer


logging.getLogger().handlers = []
logger = logging_formatter.get_configured_logger("parcels")
conn_blueprints = None
conn_parcels = None
secret_msp_connection = None
secret_parcel_connection = None


def get_now():
    return int(round(time.time() * 1000))

def get_response(body, code):
    return {
        "isBase64Encoded": False,
        "statusCode": code,
        "headers": {},
        "body": body
    }


def get_connection_parcel():
    dbname = os.environ.get("database_name")
    secret_name_param = os.environ.get("secret_name")
    init_time = get_now()
    global conn_parcels
    if conn_parcels is None or conn_parcels.closed != 0:
        conn_parcels = db.get_connection_with_secret(True, dbname,
                                                        get_secret_msp_connection(secret_name_param))
        logger.info("New connection created")
    logger.info(f'get parcels connection timing:  {get_now() - init_time}')
    return conn_parcels


def get_connection_blueprints(dbname, secret_name_param):
    init_time = get_now()
    global conn_blueprints
    if conn_blueprints is None or conn_blueprints.closed != 0:
        conn_blueprints = db.get_connection_with_secret(True, dbname,
                                                        get_secret_msp_connection(secret_name_param))
        logger.info("New connection created")
    logger.info(f'get blueprints connection timing:  {get_now() - init_time}')
    return conn_blueprints


def get_secret_msp_connection(secret_name):
    global secret_msp_connection
    init_time = get_now()
    if secret_msp_connection is None:
        secret_msp_connection = secrets_manager.get_secret(secret_name)
        logger.info("secret_msp_connection requested")
    logger.info(f'get_secret_msp_connection timing:  {get_now() - init_time}')
    return secret_msp_connection


def get_parcel(event, context):
    logger.info(event)
    global conn_parcels
    try:
        try:
            wkt = event.get("wkt")
            buffer = event.get("buffer", None)
            asking_external = event.get("external", None)
            asking_synthetic = event.get("synthetic", None)
            if buffer is not None:
                buffer = float(buffer)
        except Exception as error:
            logger.error(error)
            return get_response(json.dumps({'message': 'Bad request'}), '400')

        conn_parcels = get_connection_parcel()
        parcels = dao.get_parcels_by_geometry(conn_parcels, logger, wkt, buffer)
        if parcels is not None:
            parcel_too_big = False
            if len(parcels) == 1:
                area = parcels[0]["area"]
                if area > int(os.environ.get("parcel_big_size")):
                    logger.info("The area of the parcel is too big")
                    parcel_too_big = True
            if not parcel_too_big:
                fields_to_detokenize = {"siteAddress", "zip"}
                Tokenizer.detokenize_object_list(parcels, fields_to_detokenize)
                logger.info(parcels[0])

        if parcels is None or parcel_too_big:
            if asking_synthetic:
                logger.info("asking synthetic parcel")
                parcels = get_geojson_synthetic_parcel(wkt, logger)
            if parcels is None:
                if asking_external:
                    parcels = get_geojson_external_parcel(wkt, logger)

        if parcels is None:
            return get_response(json.dumps({'message': 'No parcel'}), '204')

        geojson = parcels_to_geojson(parcels)
        return get_response(json.dumps(geojson), '200')
    
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        return get_response(json.dumps({'message': 'Internal Server Error'}), '500')


def get_geojson_synthetic_parcel(wkt, logger):
    try:
        parcel_db_response = get_parcel_from_db(wkt);
        if parcel_db_response is not None:
            logger.info("synthetic: %s", parcel_db_response)
            parcels = []
            parcel = {'geometry': mapping(loads(json.loads(parcel_db_response["body"])["parcel"]))}
            parcels.append(parcel)
            return parcels
        return None
    except Exception as error:
        logger.error(error)
        return None


def get_parcel_from_db(wkt):
    conn = None
    try:
        conn = get_connection_blueprints("database_name_blueprints", "secret_name_msp")
        parcel_wkt = blueprints_dao.get_parcel_from_voronoi(conn, logger, wkt)
        if parcel_wkt:
            return get_response(json.dumps({'parcel': parcel_wkt}), '200')
        else:
            return get_response(json.dumps({'message': 'No parcel found'}), '204')

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        return get_response(json.dumps({'message': 'Internal Server Error'}), '500')

    finally:
        # closing database connection.
        if conn is not None:
            conn.close()


def get_geojson_external_parcel(wkt, logger):
    try:

        url = "http://parcelstream.com/GetByGeometry.aspx?geo=" + wkt \
              + "&datasource=SS.Base.Parcels/Parcels&fields=*&showSchema=false&returnFullWkt=true"

        headers = {
            'SS_KEY': '7E8AE49F-C7E4-4EDA-86EF-AF1A9A5C87F0'
        }
        response = requests.get(url, params=None, headers=headers)
        logger.info(response.content)
        root = ET.fromstring(response.content)
        for parcel in root.iter('Row'):
            parcels = []
            logger.info(parcel.attrib)
            parcel = {'geometry': mapping(loads(parcel.attrib['GEOMETRY']))}
            parcels.append(parcel)
            return parcels
        return None
    except Exception as error:
        logger.error(error)
        return None


def parcels_to_geojson(parcel_list):
    geojson = {'type': 'FeatureCollection', 'features': []}
    for parcel in parcel_list:
        feature = {'type': 'Feature',
                   'properties': {},
                   'geometry': parcel["geometry"]}
        pairs = parcel.items()
        for key, value in pairs:
            if key != "geometry":
                feature['properties'][key] = value
        geojson['features'].append(feature)
    return geojson

