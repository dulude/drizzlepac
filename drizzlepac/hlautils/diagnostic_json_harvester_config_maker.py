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
        print(json_filetype)
        output_json_dict = process_json_filetype(json_filetype, output_json_dict)
    pdb.set_trace()
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

        # add "header" section
        if "header" not in output_json_dict.keys():
            output_json_dict['header'] = []
            for header_item in json_data['header'].keys():
                output_json_dict['header'].append(header_item)
    else:
        print("     No {} files found!".format(json_filetype))
    return output_json_dict


# ======================================================================================================================

if __name__ == "__main__":
    make_config_file()