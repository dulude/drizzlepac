#!/usr/bin/env python

"""script to generate an initial starting version of the configuration .json file to drive
diagnostic_json_harvester.py"""

# Standard library imports
import glob
import json
import pdb

# Local application imports
import drizzlepac.hlautils.diagnostic_utils as du


def make_config_file():
    filetype_list = []
    json_file_list = glob.glob("*_svm_*.json")
    for json_filename  in json_file_list:
        json_filetype = json_filename.split("_svm_")[1]
        if json_filetype not in filetype_list:
            filetype_list.append(json_filetype)
            print(json_filename)
            json_data = du.read_json_file(json_filename)
            pdb.set_trace()


# ======================================================================================================================

if __name__ == "__main__":
    make_config_file()