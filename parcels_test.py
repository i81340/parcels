import sys
import os
from parcels import handler


def get_parcel_test():
    os.environ['secret_name'] = "parcels-db-connection"
    os.environ['database_name'] = "parcels"

    os.environ['secret_name_msp'] = "msp-db-connection"
    os.environ['database_name_blueprints'] = "msp-beta-legacy"
    os.environ['parcel_big_size'] = "100"

    # event = {'wkt': 'value1', 'buffer': 'value2'}
    # event = {'wkt': 'POINT(-99.744936896409 32.356796683237)', 'buffer': '0.01', 'synthetic': 'true', 'external': 'true'}
    event = {'wkt': 'POINT(-99.744936896409 32.356796683237)', 'synthetic': 'true',
             'external': 'true'}
    json = handler.get_parcel(event, None)
    print(json)


if __name__ == '__main__':
    get_parcel_test()
    sys.exit()


