from datetime import datetime
import os
import sys
import configparser
import qgis.core
import qgis.PyQt
import osgeo.gdal
import re
from zipfile import ZipFile
import math


def getDateTime():
    current_datetime = datetime.now()
    # convert the month to lowercase
    month = current_datetime.strftime("%b").lower()
    day = str(current_datetime.day).zfill(2)
    hour = str(current_datetime.hour).zfill(2)
    minute = str(current_datetime.minute).zfill(2)
    second = str(current_datetime.second).zfill(2)
    return f'{day}{month}_{hour}h{minute}m{second}s'


def get_version_from_metadata():

    current_dir = os.path.dirname(
        os.path.abspath(__file__))  # path to the current file
    plugin_dir = os.path.dirname(current_dir)  # path to the plugin folder

    file_path = os.path.join(plugin_dir, 'metadata.txt')

    config = configparser.ConfigParser()
    config.read(file_path)

    if 'general' in config and 'version' in config['general']:
        return config['general']['version']

    return ""


def get_qgis_info():
    qgis_info = {}
    qgis_info['QGIS version'] = qgis.core.Qgis.QGIS_VERSION
    qgis_info['Qt version'] = qgis.PyQt.QtCore.QT_VERSION_STR
    qgis_info['Python version'] = sys.version
    qgis_info['GDAL version'] = osgeo.gdal.VersionInfo('RELEASE_NAME')
    qgis_info['Accessibility plugin version'] = get_version_from_metadata()
    return qgis_info


def is_valid_folder_name(folder_name):
    # check for the presence of invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, folder_name):
        return False

    # check the length of the folder name
    if len(folder_name) == 0 or len(folder_name) > 255:
        return False
    return True


def get_prefix_alias(PT, protocol, mode, timetable=None, field_name="", layer="", full_prefix=True):
    """
    Point/Region - P/R  (protocol 2,1)
    Forward/Backward - F/B (mode 1,2)
    Fixed/Scheduled - X/S  (false,true)
    """
    prefix = "PT" if PT else "CAR"
    protocol_char = "R" if protocol == 1 else "P"
    mode_char = "F" if mode == 1 else "B"
    timetable_char = "" if timetable is None else ("S" if timetable else "X")

    result = f"{prefix}_{protocol_char}{mode_char}{timetable_char}"
    if full_prefix:
        if field_name:
            result = f"{result}_{field_name}"
    
    return result


def zip_directory(directory):
    file_list = ['stops.txt', 'trips.txt', 'routes.txt',
                 'stop_times.txt', 'calendar.txt', 'rev_stop_times.txt']
    timestamp = getDateTime()
    zip_name = os.path.join(directory, f'gtfs_{timestamp}.zip')
    with ZipFile(zip_name, 'w') as zipf:
        for file_name in file_list:
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                relative_path = os.path.relpath(file_path, directory)
                zipf.write(file_path, relative_path)
                os.remove(file_path)

def convert_meters_to_degrees(distance_in_meters, latitude):
    # length of one degree of longitude at a given latitude in meters
    meters_per_degree_longitude = 111320 * math.cos(math.radians(latitude))
    # convert distance from meters to degrees
    return distance_in_meters / meters_per_degree_longitude


def convert_distance_to_meters(distance_in_degrees, latitude):
    # average length of one degree at the equator (in meters)
    meters_per_degree_latitude = 111132.92 - 559.82 * \
        math.cos(2 * math.radians(latitude)) + 1.175 * \
        math.cos(4 * math.radians(latitude))
    meters_per_degree_longitude = meters_per_degree_latitude * \
        math.cos(math.radians(latitude))
    return round(distance_in_degrees * meters_per_degree_longitude)
