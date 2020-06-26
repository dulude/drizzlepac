#!/usr/bin/env python

"""This script harvests """


# Standard library imports
import argparse
import logging
import os
import pdb
import sys

from bokeh.layouts import gridplot, row
from bokeh.plotting import figure, output_file, show, save
from bokeh.models import ColumnDataSource, Label
from bokeh.models.tools import HoverTool

# Local application imports
from drizzlepac.haputils.pandas_utils import PandasDFReader
from stsci.tools import logutil

def n_gaia_soruces_graphics_driver(dataframe_filename, output_base_filename='n_gaia_sources_graphics', log_level=logutil.logging.NOTSET):
    """This is the primary driver subroutine for this script.
    P
    :param dataframe_filename:
    :param output_base_filename:
    :param log_level:
    :return:
    """


    # 1: get relevant data values from user-specified input file

    # 2: generate visualization with bokeh


# ======================================================================================================================


if __name__ == "__main__":
    # Process command-line inputs with argparse
    parser = argparse.ArgumentParser(description='Read the harvested Pandas dataframe stored as and HDF5 file.')

    parser.add_argument('dataframe_filename', help='File which holds the Pandas dataframe in an HDF5 file.')
    parser.add_argument('-o', '--output_base_filename', required=False, default="n_gaia_sources_graphics",
                        help='Name of the output base filename (filename without the extension) for the  '
                             'HTML file generated by Bokeh. Unless explicitly specified, the default value '
                             'is "n_gaia_sources_graphics".'
                             ' ')
    parser.add_argument('-l', '--log_level', required=False, default='info',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        help='The desired level of verboseness in the log statements displayed on the screen '
                             'and written to the .log file. The level of verboseness from left to right, and '
                             'includes all log statements with a log_level left of the specified level. '
                             'Specifying "critical" will only record/display "critical" log statements, and '
                             'specifying "error" will record/display both "error" and "critical" log '
                             'statements, and so on.')
    user_args = parser.parse_args()

    # Set up logging
    log_dict = {"critical": logutil.logging.CRITICAL,
                "error": logutil.logging.ERROR,
                "warning": logutil.logging.WARNING,
                "info": logutil.logging.INFO,
                "debug": logutil.logging.DEBUG}
    log_level = log_dict[user_args.log_level]
    log.setLevel(log_level)

    # Verify the input file exists
    if not os.path.exists(user_args.dataframe_filename):
        err_msg = "Harvester HDF5 File {} does not exist.".format(user_args.dataframe_filename)
        log.critical(err_msg)
        raise Exception(err_msg)

    print(user_args.output_base_filename)

    n_gaia_soruces_graphics_driver(user_args.dataframe_filename,
                                   output_base_filename=user_args.output_base_filename,
                                   log_level=log_level)