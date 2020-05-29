#!/usr/bin/env python

"""script to generate an initial starting version of the configuration .json file to drive
diagnostic_json_harvester.py"""

# Standard library imports
import collections
import glob
import json
import os
import pdb

# Local application imports
import drizzlepac.hlautils.diagnostic_utils as du

def add_meta_item(dd):
    dd=collections.OrderedDict(dd)
    dd['meta'] = "Human-readable title placeholder"
    dd.move_to_end('meta', last=False)
    for k in dd.keys():
        if isinstance(dd[k], dict):
            dd[k] = add_meta_item(dd[k])
    return dd
# ------------------------------------------------------------------------------------------------------------


def convert_nested(dct):
    # empty dict to store the result
    result = dict()

    # create an iterator of lists
    # representing nested or hierarchial flow
    lsts = ([*k.split("."), v] for k, v in dct.items())

    # insert each list into the result
    for lst in lsts:
        insert(result, lst)
    return result
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

def insert(dct, lst):
    for x in lst[:-2]:
        dct[x] = dct = dct.get(x, dict())
    dct.update({lst[-2]: lst[-1]})

# ------------------------------------------------------------------------------------------------------------

def make_config_file():
    """Main calling subroutine"""
    # Create list of json filetypes
    json_filetype_list = []
    split_string = "_svm_"
    for json_filename in glob.glob("*{}*.json".format(split_string)):
        json_filetype = split_string+json_filename.split(split_string)[1]
        if json_filetype not in json_filetype_list:
            json_filetype_list.append(json_filetype)
    del(json_filetype)
    
    # process each json filetype
    output_json_dict = collections.OrderedDict()
    for json_filetype in json_filetype_list:
        output_json_dict = process_json_filetype(json_filetype, output_json_dict)

    # write out output_json_dict to a json file
    output_json_filename = 'json_harvester_config.json'
    if os.path.exists(output_json_filename):
        os.remove(output_json_filename)
    with open(output_json_filename, 'w') as f:
        json.dump(output_json_dict, f, indent=4)
    print("Wrote ",output_json_filename)
# ------------------------------------------------------------------------------------------------------------


def process_json_filetype(json_filetype, output_json_dict):
    """builds new section in output_json_dict based on the information stored in, and the the structure of
    specified json filetype.

    Parameters
    ----------
    json_filetype : str
        the type of json file to process.

    output_json_dict : ordered dictionary
        ordered dictionary containing information that tells json_harvester how to process each type of json
        file

    Returns
    -------
    output_json_dict : ordered dictionary
        ordered dictionary containing information that tells json_harvester how to process each type of json
        file updated to include information from the json filetype specified in json_filetype.
    """
    json_files = glob.glob("*"+json_filetype)
    if json_files:
        json_filename = json_files[0]
        print("json file: ",json_filename)
        json_data = du.read_json_file(json_filename)

        # add "header" section just once
        if "header" not in output_json_dict.keys():
            output_json_dict['header'] = []
            for header_item in json_data['header'].keys():
                output_json_dict['header'].append(header_item)

        # add "general information" section just once
        if "general information" not in output_json_dict.keys():
            output_json_dict['general information'] = collections.OrderedDict()
            for gi_item in json_data['general information'].keys():
                output_json_dict['general information'][gi_item] = "Human-readable title placeholder"

        # update output_json_dict with information about the specified json file type
        # flatten out nested dictionaries
        flattened_data = flatten_dict(json_data['data'])
        out_flattened_data = collections.OrderedDict()

        # replace all values with a placeholder tuple
        placeholder_tuple = ("Human-readable title placeholder", "units placeholder")
        for flat_key in flattened_data.keys():
            # extract column names from embedded astropy tables and add them to the dictionary
            if str(type(flattened_data[flat_key])) == "<class 'astropy.table.table.Table'>":
                for coltitle in flattened_data[flat_key].colnames:
                    out_flattened_data["{}.{}".format(flat_key,coltitle)] = placeholder_tuple
            else:
                out_flattened_data[flat_key] = placeholder_tuple
        for flat_key in out_flattened_data.keys(): # TODO: REMOVE
            nest_level = len(flat_key.split(".")) # TODO: REMOVE
            print("     {}{}{}".format("      "*nest_level,flat_key,out_flattened_data[flat_key])) # TODO: REMOVE
        # re-nest flattened dictionary and update output_json_dict
        out_dict = collections.OrderedDict(convert_nested(out_flattened_data))
        out_dict = add_meta_item(out_dict)
        output_json_dict[json_filetype] = out_dict
    else:
        print("     No {} files found!".format(json_filetype))
    return output_json_dict


# ======================================================================================================================

if __name__ == "__main__":
    make_config_file()

# TODO: Figure out how to deal with custom-named "PrimaryWCS_ippsss" _svm_wcs.json subsections