#!/usr/bin/env python

"""This script 'harvests' information stored in the .json files produced by
drizzlepac/haputils/svm_quality_analysis.py and stores it as a Pandas DataFrame"""

# Standard library imports
import argparse
import collections
import glob
import os
import pdb
import sys

# Related third party imports
import pandas as pd

# Local application imports
import drizzlepac.haputils.diagnostic_utils as du
from stsci.tools import logutil

__taskname__ = 'diagnostic_json_harvester'

MSG_DATEFMT = '%Y%j%H%M%S'
SPLUNK_MSG_FORMAT = '%(asctime)s %(levelname)s src=%(name)s- %(message)s'
log = logutil.create_logger(__name__, level=logutil.logging.NOTSET, stream=sys.stdout,
                            format=SPLUNK_MSG_FORMAT, datefmt=MSG_DATEFMT)

# ------------------------------------------------------------------------------------------------------------


def filter_header_info(unfiltered_header):
    """removes unwanted/unneeded keywords from header according to various rules prior to insertion to pandas
    DataFrame ingest dictionary.

    NOTE: For the time being, this subroutine is an inert placeholder. In the near future, header keywords
    will be filtered using a keyword whitelist stored in a json harvester settings parameter file.

    Parameters
    ----------
    unfiltered_header : dictionary
        dictionary of unfiltered header information to process

    Returns
    -------
    filtered_header : dictionary
        filtered version of input dictionary *unfiltered_header*
    """
    # TODO: IMPLEMENT KEYWORD FILTERING AT A LATER DATE!
    filtered_header = unfiltered_header
    return filtered_header

# ------------------------------------------------------------------------------------------------------------


def flatten_dict(dd, separator='.', prefix=''):
    """Recursive subroutine to flatten nested dictionaries down into a single-layer dictionary.
    Borrowed from https://www.geeksforgeeks.org/python-convert-nested-dictionary-into-flattened-dictionary/

    Parameters
    ----------
    dd : dict
        dictionary to flatten

    separator : str, optional
        separator character used in constructing flattened dictionary key names from multiple recursive
        elements. Default value is '.'

    prefix : str, optional
        flattened dictionary key prefix. Default value is an empty string ('').

    Returns
    -------
    a version of input dictionary *dd* that has been flattened by one layer
    """
    return {prefix + separator + k if prefix else k: v
            for kk, vv in dd.items()
            for k, v in flatten_dict(vv, separator, kk).items()
            } if isinstance(dd, dict) else {prefix: dd}

# ------------------------------------------------------------------------------------------------------------


def get_json_files(search_path=os.getcwd(), log_level=logutil.logging.INFO):
    """use glob to create a list of json files to harvest

    Parameters
    ----------
    search_path : str, optional
        directory path to search for .json files. Default value is the current working directory.

    log_level : int, optional
        The desired level of verboseness in the log statements displayed on the screen and written to the
        .log file. Default value is 'INFO'.

    Returns
    -------
    out_json_dict : ordered dictionary
        dictionary containing lists of all identified json files, grouped by and  keyed by Pandas DataFrame
        index value
    """
    log.setLevel(log_level)

    # set up search string and use glob to get list of files
    search_string = os.path.join(search_path, "*_svm_*.json")
    json_list = glob.glob(search_string)

    # store json filenames in a dictionary keyed by Pandas DataFrame index value
    if json_list:
        out_json_dict = collections.OrderedDict()
        for json_filename in sorted(json_list):
            json_data = du.read_json_file(json_filename)
            dataframe_idx = json_data['general information']['dataframe_index']
            if dataframe_idx in out_json_dict.keys():
                out_json_dict[dataframe_idx].append(json_filename)
            else:
                out_json_dict[dataframe_idx] = [json_filename]
            del(json_data)  # Housekeeping!

    # Fail gracefully if no .json files were found
    else:
        err_msg = "No .json files were found!"
        log.error(err_msg)
        raise Exception(err_msg)
    return out_json_dict

# ------------------------------------------------------------------------------------------------------------


def h5load(filename):
    """Load pandas DataFrame and metadata stored in specified HDF5 file.
    Code borrowed from https://stackoverflow.com/questions/29129095/save-additional-attributes-in-pandas-dataframe/29130146#29130146

    Parameters
    ----------
    filename : str
        Name of the HDF5 file to open

    Returns
    -------
    data : Pandas DataFrame
        Pandas Dataframe read in from specified HDF5 file

    metadata : dict
        dictionary containing dataFrame metadata
    """
    if os.path.exists(filename):
        with pd.HDFStore(filename) as store:
            data = store['mydata']
            metadata = store.get_storer('mydata').attrs.metadata
    else:
        errmsg = "HDF5 file {} not found!".format(filename)
        log.error(errmsg)
        raise Exception(errmsg)
    return data, metadata


# ------------------------------------------------------------------------------------------------------------

def h5store(filename, df, **kwargs):
    """Write a pandas Dataframe and metadata to a HDF5 file.
    Code borrowed from https://stackoverflow.com/questions/29129095/save-additional-attributes-in-pandas-dataframe/29130146#29130146

    Parameters
    ----------
    filename : str
        Name of the output HDF5 file

    df : Pandas DataFrame
        Pandas DataFrame to write to output file

    Returns
    -------
    Nothing.
    """
    store = pd.HDFStore(filename)
    store.put('mydata', df)
    store.get_storer('mydata').attrs.metadata = kwargs
    store.close()


# ------------------------------------------------------------------------------------------------------------

def json_harvester(json_search_path=os.getcwd(), log_level=logutil.logging.INFO,
                   output_filename="svm_qa_dataframe.csv"):
    """Main calling function

    Parameters
    ----------
    json_search_path : str, optional
        The full path of the directory that will be searched for json files to process. If not explicitly
        specified, the current working directory will be used.

    log_level : int, optional
        The desired level of verboseness in the log statements displayed on the screen and written to the
        .log file. Default value is 'INFO'.

    output_filename : str, optional
        Name of the output .csv file that the Pandas DataFrame will be written to. If not explicitly
        specified, the DataFrame will be written to the file 'svm_qa_dataframe.csv' in the current working
        directory.
    """
    log.setLevel(log_level)

    # Get sorted list of json files
    json_dict = get_json_files(search_path=json_search_path, log_level=log_level)
    master_dataframe = None
    # extract all information from all json files related to a specific Pandas DataFrame index value into a
    # single line in the master dataframe
    for idx in json_dict.keys():
        ingest_dict = make_dataframe_line(json_dict[idx], log_level=log_level)
        if ingest_dict:
            if master_dataframe is not None:
                log.debug("APPENDED DATAFRAME")
                master_dataframe = master_dataframe.append(pd.DataFrame(ingest_dict["data"], index=[idx]))
                for key_item in ingest_dict['descriptions'].keys():
                    if key_item not in metadata['descriptions'].keys(): # only have to check descriptions dict because units dict has same keys
                        metadata['descriptions'][key_item] = ingest_dict['descriptions'][key_item]
                        metadata['units'][key_item] = ingest_dict['units'][key_item]
            else:
                log.debug("CREATED DATAFRAME")
                master_dataframe = pd.DataFrame(ingest_dict["data"], index=[idx])
                metadata = {}
                metadata['descriptions'] = ingest_dict['descriptions']
                metadata['units'] = ingest_dict['units']

    # Write master_dataframe out to a HDF5 .hdfile
    if master_dataframe is not None:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        h5store(output_filename, master_dataframe, **metadata)
        log.info("Wrote dataframe to HDF5 file {}".format(output_filename))

        output_csvfile = output_filename.replace(".h5", ".csv")
        if log_level == logutil.logging.DEBUG:
            if os.path.exists(output_csvfile):
                os.remove(output_csvfile)
            master_dataframe.to_csv(output_csvfile)
            log.debug("Wrote dataframe to csv file {}".format(output_csvfile))

# ------------------------------------------------------------------------------------------------------------


def make_dataframe_line(json_filename_list, log_level=logutil.logging.INFO):
    """extracts information from the json files specified by the input list *json_filename_list*.

    Parameters
    ----------
    json_filename_list : list
        list of json files to process

    log_level : int, optional
        The desired level of verboseness in the log statements displayed on the screen and written to the
        .log file. Default value is 'INFO'.

    Returns
    -------
    ingest_dict : collections.OrderedDict
        ordered dictionary containing all information extracted from json files specified by the input list
        *json_filename_list*.
    """
    log.setLevel(log_level)
    header_ingested = False
    gen_info_ingested = False
    ingest_dict = collections.OrderedDict()
    ingest_dict['data'] = collections.OrderedDict()
    ingest_dict['descriptions'] = collections.OrderedDict()
    ingest_dict['units'] = collections.OrderedDict()
    for json_filename in json_filename_list:
        # This is to differentiate point catalog compare_sourcelists columns from segment catalog
        # compare_sourcelists columns in the dataframe
        if json_filename.endswith("_point-cat_svm_compare_sourcelists.json"):
            title_suffix = "hap_vs_hla_point_"
        elif json_filename.endswith("_segment-cat_svm_compare_sourcelists.json"):
            title_suffix = "hap_vs_hla_segment_"
        else:
            title_suffix = ""
        json_data = du.read_json_file(json_filename)
        # add information from "header" section to ingest_dict just once
        if not header_ingested:
            filtered_header = filter_header_info(json_data['header'])
            for header_item in filtered_header.keys():
                ingest_dict["data"]["header."+header_item] = filtered_header[header_item]
            header_ingested = True

        # add information from "general information" section to ingest_dict just once
        if not gen_info_ingested:
            for gi_item in json_data['general information'].keys():
                ingest_dict["data"]["gen_info."+gi_item] = json_data['general information'][gi_item]
            gen_info_ingested = True

        # recursively flatten nested "data" section dictionaries and build ingest_dict
        flattened_data = flatten_dict(json_data['data'])
        flattened_descriptions = flatten_dict(json_data['descriptions'])
        flattened_units = flatten_dict(json_data['units'])
        for fd_key in flattened_data.keys():
            json_data_item = flattened_data[fd_key]
            ingest_key = fd_key.replace(" ", "_")
            if str(type(json_data_item)) == "<class 'astropy.table.table.Table'>":
                for coltitle in json_data_item.colnames:
                    ingest_value = json_data_item[coltitle].tolist()
                    id_key = title_suffix + ingest_key + "." + coltitle
                    ingest_dict["data"][id_key] = [ingest_value]
                    try:
                        ingest_dict["descriptions"][id_key] = flattened_descriptions[title_suffix + fd_key + "." + coltitle]
                    except:  # insert placeholders if the code runs into trouble getting descriptions
                        log.warning("Descriptions not found for {}. Using placeholder value '>>>UNDEFINED<<<' instead.".format(id_key))
                        ingest_dict["descriptions"][id_key] = ">>>UNDEFINED<<<"
                    try:
                        ingest_dict["units"][id_key] = flattened_units[title_suffix + fd_key + "." + coltitle]
                    except:  # insert placeholders if the code runs into trouble getting units
                        log.warning("Units not found for {}. Using placeholder value '>>>UNDEFINED<<<' instead.".format(id_key))
                        ingest_dict["units"][id_key] = ">>>UNDEFINED<<<"
            else:
                ingest_value = json_data_item
                id_key = title_suffix + ingest_key
                ingest_dict["data"][id_key] = ingest_value
                try:
                    ingest_dict["descriptions"][id_key] = flattened_descriptions[fd_key]
                except:  # insert placeholders if the code runs into trouble getting the descriptions
                    log.warning("Descriptions not found for {}. Using placeholder value '>>>UNDEFINED<<<' instead.".format(id_key))
                    ingest_dict["descriptions"][id_key] = ">>>UNDEFINED<<<"
                try:
                    ingest_dict["units"][id_key] = flattened_units[fd_key]
                except:  # insert placeholders if the code runs into trouble getting units
                    log.warning("Units not found for {}. Using placeholder value '>>>UNDEFINED<<<' instead.".format(id_key))
                    ingest_dict["units"][id_key] = ">>>UNDEFINED<<<"
    return ingest_dict

# ======================================================================================================================


if __name__ == "__main__":
    # process command-line inputs with argparse
    parser = argparse.ArgumentParser(description='ingest all SVM QA json files into a Pandas DataFrame and'
                                                 'and write DataFrame to an .csv file.')
    parser.add_argument('-j', '--json_search_path', required=False, default=os.getcwd(),
                        help='The full path of the directory that will be searched for json files to '
                             'process. If not explicitly specified, the current working directory will be '
                             'used.')
    parser.add_argument('-l', '--log_level', required=False, default='info',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        help='The desired level of verboseness in the log statements displayed on the screen '
                             'and written to the .log file. The level of verboseness from left to right, and '
                             'includes all log statements with a log_level left of the specified level. '
                             'Specifying "critical" will only record/display "critical" log statements, and '
                             'specifying "error" will record/display both "error" and "critical" log '
                             'statements, and so on.')
    parser.add_argument('-o', '--output_filename', required=False, default="svm_qa_dataframe.h5",
                        help='Name of the output Hierarchical Data Format version 5 (HDF5) .h5 file that the '
                             'Pandas DataFrame will be written to. If not explicitly specified, the '
                             'DataFrame will be written to the file "svm_qa_dataframe.h5" in the current '
                             'working directory')
    user_args = parser.parse_args()

    # set up logging
    log_dict = {"critical": logutil.logging.CRITICAL,
                "error": logutil.logging.ERROR,
                "warning": logutil.logging.WARNING,
                "info": logutil.logging.INFO,
                "debug": logutil.logging.DEBUG}
    log_level = log_dict[user_args.log_level]
    log.setLevel(log_level)

    json_harvester(json_search_path=user_args.json_search_path,
                   log_level=log_level,
                   output_filename=user_args.output_filename)