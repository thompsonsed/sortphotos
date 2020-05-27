#!/usr/bin/env python
# encoding: utf-8
"""
sortphotos.py

Created on 3/2/2013
Copyright (c) S. Andrew Ning. All rights reserved.

Updated by Sam Thompson

"""

from __future__ import print_function
from __future__ import with_statement

import itertools
import logging
import math
import pathlib
import subprocess
import os
import sys
import shutil
import exiftool
import pytz
from tqdm import tqdm

try:
    import json
except:
    import simplejson as json
import filecmp
from datetime import datetime, timedelta
from dateutil import parser
import re
import locale

# Setting locale to the 'local' value
locale.setlocale(locale.LC_ALL, '')

exiftool_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Image-ExifTool', 'exiftool')


# -------- convenience methods -------------

def parse_date_exif(date_string):
    """
    extract date info from EXIF data
    YYYY:MM:DD HH:MM:SS
    or YYYY:MM:DD HH:MM:SS+HH:MM
    or YYYY:MM:DD HH:MM:SS-HH:MM
    or YYYY:MM:DD HH:MM:SSZ
    """
    # First 19 chars are year/month/day/hour/min/sec
    output_date_time = None
    for f in ["%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"]:
        try:
            output_date_time = datetime.strptime(date_string, f)
        except ValueError:
            pass
    if output_date_time is None:
        raise ValueError("Could not parse {}.".format(date_string))
    if output_date_time.tzinfo is None:
        output_date_time = pytz.utc.localize(output_date_time)
    return output_date_time
    #
    # # split into date and time
    # elements = str(date_string).strip().split()  # ['YYYY:MM:DD', 'HH:MM:SS']
    #
    # if len(elements) < 1:
    #     return None
    #
    # # parse year, month, day
    # date_entries = elements[0].split(':')  # ['YYYY', 'MM', 'DD']
    #
    # # check if three entries, nonzero data, and no decimal (which occurs for timestamps with only time but no date)
    # if len(date_entries) == 3 and date_entries[0] > '0000' and '.' not in ''.join(date_entries):
    #     year = int(date_entries[0])
    #     month = int(date_entries[1])
    #     day = int(date_entries[2])
    # else:
    #     return None
    #
    # # parse hour, min, second
    # time_zone_adjust = False
    # hour = 12  # defaulting to noon if no time data provided
    # minute = 0
    # second = 0
    #
    # if len(elements) > 1:
    #     time_entries = re.split('(\+|-|Z)', elements[1])  # ['HH:MM:SS', '+', 'HH:MM']
    #     time = time_entries[0].split(':')  # ['HH', 'MM', 'SS']
    #
    #     if len(time) == 3:
    #         hour = int(time[0])
    #         minute = int(time[1])
    #         second = int(time[2].split('.')[0])
    #     elif len(time) == 2:
    #         hour = int(time[0])
    #         minute = int(time[1])
    #
    #     # adjust for time-zone if needed
    #     if len(time_entries) > 2:
    #         time_zone = time_entries[2].split(':')  # ['HH', 'MM']
    #
    #         if len(time_zone) == 2:
    #             time_zone_hour = int(time_zone[0])
    #             time_zone_min = int(time_zone[1])
    #
    #             # check if + or -
    #             if time_entries[1] == '+':
    #                 time_zone_hour *= -1
    #
    #             dateadd = timedelta(hours=time_zone_hour, minutes=time_zone_min)
    #             time_zone_adjust = True
    #
    # # form date object
    # try:
    #     date = datetime(year, month, day, hour, minute, second)
    # except ValueError:
    #     return None  # errors in time format
    #
    # # try converting it (some "valid" dates are way before 1900 and cannot be parsed by strtime later)
    # try:
    #     date.strftime('%Y/%m-%b')  # any format with year, month, day, would work here.
    # except ValueError:
    #     return None  # errors in time format
    #
    # # adjust for time zone if necessary
    # if time_zone_adjust:
    #     date += dateadd
    #
    # return date


def get_oldest_timestamp(data, additional_groups_to_ignore, additional_tags_to_ignore, print_all_tags=False):
    """data as dictionary from json.  Should contain only time stamps except SourceFile"""

    # save only the oldest date
    date_available = False
    oldest_date = None
    oldest_keys = []

    # save src file
    src_file = data['SourceFile']

    # ssetup tags to ignore
    ignore_groups = ['ICC_Profile'] + additional_groups_to_ignore
    ignore_tags = ['SourceFile', 'XMP:HistoryWhen'] + additional_tags_to_ignore

    # First check if the original key is there
    date_time_original_key = "EXIF:DateTimeOriginal"
    try:
        oldest_date = parse_date_exif(data[date_time_original_key])
        oldest_keys = [date_time_original_key]
        date_available = True
    except (KeyError, ValueError):
        for key, date in data.items():
            if "date" in key.lower() or "time" in key.lower():
                try:
                    exifdate = parse_date_exif(str(date))
                except ValueError:
                    continue
                if oldest_date is None or exifdate < oldest_date:
                    oldest_date = exifdate
                    date_available = True
                    oldest_keys = [key]
                elif exifdate == oldest_date:
                    oldest_keys.append(key)

    #
    #
    # for key in data.keys():
    #     # check if this key needs to be ignored, or is in the set of tags that must be used
    #     if (key not in ignore_tags) and (key.split(':')[0] not in ignore_groups) and 'GPS' not in key:
    #         date = data[key]
    #         if print_all_tags:
    #             logging.info(str(key) + ', ' + str(date))
    #         # (rare) check if multiple dates returned in a list, take the first one which is the oldest
    #         if isinstance(date, list):
    #             date = date[0]
    #         try:
    #             # exifdate = parse_date_exif(date)  # check for poor-formed exif data, but allow continuation
    #             exifdate = parser.parse(str(date))
    #             if exifdate.tzinfo is None:
    #                 exifdate = pytz.utc.localize(exifdate)
    #         except ValueError as e:
    #             exifdate = None
    #         if exifdate:
    #             if oldest_date is None or exifdate < oldest_date:
    #                 oldest_date = exifdate
    #                 date_available = True
    #                 oldest_keys = [key]
    #             elif exifdate and exifdate == oldest_date:
    #                 oldest_keys.append(key)

    if not date_available:
        oldest_date = None

    return src_file, oldest_date, oldest_keys


def get_all_files(path: pathlib.Path, recursive=False):
    paths = []
    for i in path.iterdir():
        if i.is_dir() and recursive:
            paths.extend(get_all_files(i, recursive=recursive))
        else:
            paths.append(str(i))
    return paths


def check_for_early_morning_photos(date, day_begins):
    """check for early hour photos to be grouped with previous day"""

    if date.hour < day_begins:
        print('moving this photo to the previous day for classification purposes (day_begins=' + str(day_begins) + ')')
        date = date - timedelta(hours=date.hour + 1)  # push it to the day before for classificiation purposes

    return date


# #  this class is based on code from Sven Marnach (http://stackoverflow.com/questions/10075115/call-exiftool-from-a-python-script)
# class ExifTool(object):
#     """used to run ExifTool from Python and keep it open"""
#
#     sentinel = "{ready}"
#
#     def __init__(self, executable=exiftool_location, verbose=False):
#         self.executable = executable
#         self.verbose = verbose
#
#     def __enter__(self):
#         self.process = subprocess.Popen(
#             ['perl', self.executable, "-stay_open", "True", "-@", "-"],
#             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
#         return self
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.process.stdin.write(b'-stay_open\nFalse\n')
#         self.process.stdin.flush()
#
#     def execute(self, *args):
#         args = args + ("-execute\n",)
#         self.process.stdin.write(str.join("\n", args).encode('utf-8'))
#         self.process.stdin.flush()
#         output = ""
#         fd = self.process.stdout.fileno()
#         while not output.rstrip(' \t\n\r').endswith(self.sentinel):
#             increment = os.read(fd, 4096)
#             logging.info(increment.decode('utf-8'))
#             output += increment.decode('utf-8')
#         return output.rstrip(' \t\n\r')[:-len(self.sentinel)]
#
#     def get_metadata(self, *args):
#
#         try:
#             return json.loads(self.execute(*args))
#         except ValueError as ve:
#             raise ValueError("No file to parse or invalid data: {}".format(ve))


# ---------------------------------------


def sortPhotos(src_dir, dest_dir, sort_format, rename_format, recursive=False,
               copy_files=False, test=False, remove_duplicates=True, day_begins=0,
               additional_groups_to_ignore=['File'], additional_tags_to_ignore=[],
               use_only_groups=None, use_only_tags=None, keep_filename=False):
    """
    This function is a convenience wrapper around ExifTool based on common usage scenarios for sortphotos.py

    Parameters
    ---------------
    src_dir : str
        directory containing files you want to process
    dest_dir : str
        directory where you want to move/copy the files to
    sort_format : str
        date format code for how you want your photos sorted
        (https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior)
    rename_format : str
        date format code for how you want your files renamed
        (https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior)
        None to not rename file
    recursive : bool
        True if you want src_dir to be searched recursively for files (False to search only in top-level of src_dir)
    copy_files : bool
        True if you want files to be copied over from src_dir to dest_dir rather than moved
    test : bool
        True if you just want to simulate how the files will be moved without actually doing any moving/copying
    remove_duplicates : bool
        True to remove files that are exactly the same in name and a file hash
    keep_filename : bool
        True to append original filename in case of duplicates instead of increasing number
    day_begins : int
        what hour of the day you want the day to begin (only for classification purposes).  Defaults at 0 as midnight.
        Can be used to group early morning photos with the previous day.  must be a number between 0-23
    additional_groups_to_ignore : list(str)
        tag groups that will be ignored when searching for file data.  By default File is ignored
    additional_tags_to_ignore : list(str)
        specific tags that will be ignored when searching for file data.
    use_only_groups : list(str)
        a list of groups that will be exclusived searched across for date info
    use_only_tags : list(str)
        a list of tags that will be exclusived searched across for date info
    verbose : bool
        True if you want to see details of file processing

    """

    # some error checking
    if not os.path.exists(src_dir):
        raise Exception('Source directory does not exist')

    # setup arguments to exiftool
    args = ['-j', '-a', '-G']

    # setup tags to ignore
    if use_only_tags is not None:
        additional_groups_to_ignore = []
        additional_tags_to_ignore = []
        for t in use_only_tags:
            args += ['-' + t]

    elif use_only_groups is not None:
        additional_groups_to_ignore = []
        for g in use_only_groups:
            args += ['-' + g + ':Time:All']

    else:
        args += ['-time:all']

    if recursive:
        args += ['-r']

    args += [src_dir]

    # Get all files
    files = get_all_files(pathlib.Path(src_dir), recursive=recursive)

    # get all metadata
    recursive_text = "recursively " if recursive else ""
    logging.info("Getting metadata {}from {}".format(recursive_text, src_dir))
    metadata = []
    with exiftool.ExifTool() as et:
        scalar = 100
        iterator = (files[i:i + scalar] for i in range(0, len(files), scalar))
        for each in tqdm(iterator, total=len(files) / scalar, unit_scale=scalar):
            metadata.extend(et.get_metadata_batch(each))

    excluded = [x for x in metadata if "ExifTool:Error" in x.keys()]
    metadata = [x for x in metadata if "ExifTool:Error" not in x.keys()]
    logging.info(
        "Found {} files, of which {} will be parsed (ignoring {}).".format(len(files), len(metadata), len(excluded)))
    for i in excluded:
        logging.info("Ignoring {}".format(i["SourceFile"]))

    if test:
        test_file_dict = {}
    # parse output extracting oldest relevant date
    for data in tqdm(metadata):

        # extract timestamp date for photo
        src_file, date, keys = get_oldest_timestamp(data, additional_groups_to_ignore, additional_tags_to_ignore)

        # fixes further errors when using unicode characters like "\u20AC"
        src_file.encode('utf-8')

        # check if no valid date found
        if not date:
            logging.info('No valid dates were found using the specified tags.  File will remain where it is.')

        # ignore hidden files
        if os.path.basename(src_file).startswith('.'):
            logging.info('hidden file.  will be skipped')
            continue

        logging.info('Date/Time: {}'.format(date))
        logging.info('Corresponding Tags: ' + ', '.join(keys))

        # early morning photos can be grouped with previous day (depending on user setting)
        date = check_for_early_morning_photos(date, day_begins)

        # create folder structure
        dir_structure = date.strftime(sort_format)
        dirs = dir_structure.split('/')
        dest_file = dest_dir
        for thedir in dirs:
            dest_file = os.path.join(dest_file, thedir)
            if not test and not os.path.exists(dest_file):
                os.makedirs(dest_file)

        # rename file if necessary
        filename = os.path.basename(src_file)

        if rename_format is not None and date is not None:
            _, ext = os.path.splitext(filename)
            filename = date.strftime(rename_format) + ext.lower()

        # setup destination file
        dest_file = os.path.join(dest_file, filename)
        root, ext = os.path.splitext(dest_file)

        name = 'Destination '
        if copy_files:
            name += '(copy): '
        else:
            name += '(move): '
        logging.info(name + dest_file)

        # check for collisions
        append = 1
        fileIsIdentical = False

        while True:

            if (not test and os.path.isfile(dest_file)) or (
                    test and dest_file in test_file_dict.keys()):  # check for existing name
                if test:
                    dest_compare = test_file_dict[dest_file]
                else:
                    dest_compare = dest_file
                if remove_duplicates and filecmp.cmp(src_file, dest_compare):  # check for identical files
                    fileIsIdentical = True
                    logging.error('Identical file already exists at {}.  Duplicate will be ignored.'.format(src_file))
                    break

                else:  # name is same, but file is different
                    if keep_filename:
                        orig_filename = os.path.splitext(os.path.basename(src_file))[0]
                        dest_file = root + '_' + orig_filename + '_' + str(append) + ext
                    else:
                        dest_file = root + '_' + str(append) + ext
                    append += 1
                    logging.error('Same name already exists...renaming to: {}'.format(dest_file))

            else:
                break

        # finally move or copy the file
        if test:
            test_file_dict[dest_file] = src_file

        else:

            if fileIsIdentical:
                continue  # ignore identical files
            else:
                if copy_files:
                    shutil.copy2(src_file, dest_file)
                else:
                    shutil.move(src_file, dest_file)


def main():
    import argparse

    # setup command line parsing
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='Sort files (primarily photos and videos) into folders by date\nusing EXIF and other metadata')
    parser.add_argument('src_dir', type=str, help='source directory')
    parser.add_argument('dest_dir', type=str, help='destination directory')
    parser.add_argument('-r', '--recursive', action='store_true', help='search src_dir recursively')
    parser.add_argument('-c', '--copy', action='store_true', help='copy files instead of move')
    parser.add_argument('-v', '--verbose', action='store_true', help="use verbose logging")
    parser.add_argument('-vv', '--vverbose', action='store_true', help="use very verbose logging")

    parser.add_argument('-t', '--test', action='store_true',
                        help='run a test.  files will not be moved/copied\ninstead you will just a list of would happen')
    parser.add_argument('--sort', type=str, default='%Y/%m-%b',
                        help="choose destination folder structure using datetime format \n\
    https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior. \n\
    Use forward slashes / to indicate subdirectory(ies) (independent of your OS convention). \n\
    The default is '%%Y/%%m-%%b', which separates by year then month \n\
    with both the month number and name (e.g., 2012/02-Feb).")
    parser.add_argument('--rename', type=str, default=None,
                        help="rename file using format codes \n\
    https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior. \n\
    default is None which just uses original filename")
    parser.add_argument('--keep-filename', action='store_true',
                        help='In case of duplicated output filenames an increasing number and the original file name will be appended',
                        default=False)
    parser.add_argument('--remove-duplicates', dest="remove_duplicates", action="store_true",
                        help='If file is a duplicate ignore it.')
    parser.add_argument('--day-begins', type=int, default=0, help='hour of day that new day begins (0-23), \n\
    defaults to 0 which corresponds to midnight.  Useful for grouping pictures with previous day.')
    parser.add_argument('--ignore-groups', type=str, nargs='+',
                        default=[],
                        help='a list of tag groups that will be ignored for date informations.\n\
    list of groups and tags here: http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/\n\
    by default the group \'File\' is ignored which contains file timestamp data')
    parser.add_argument('--ignore-tags', type=str, nargs='+',
                        default=[],
                        help='a list of tags that will be ignored for date informations.\n\
    list of groups and tags here: http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/\n\
    the full tag name needs to be included (e.g., EXIF:CreateDate)')
    parser.add_argument('--use-only-groups', type=str, nargs='+',
                        default=None,
                        help='specify a restricted set of groups to search for date information\n\
    e.g., EXIF')
    parser.add_argument('--use-only-tags', type=str, nargs='+',
                        default=None,
                        help='specify a restricted set of tags to search for date information\n\
    e.g., EXIF:CreateDate')

    # parse command line arguments
    args = parser.parse_args()
    if args.vverbose:
        logging.getLogger().setLevel(20)
    if not args.verbose:
        logging.getLogger().setLevel(40)
    else:
        logging.getLogger().setLevel(30)
    sortPhotos(args.src_dir, args.dest_dir, args.sort, args.rename, args.recursive,
               args.copy, args.test, args.remove_duplicates, args.day_begins,
               args.ignore_groups, args.ignore_tags, args.use_only_groups,
               args.use_only_tags, args.keep_filename)


if __name__ == '__main__':
    main()
