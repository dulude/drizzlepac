#!/usr/bin/env python

"""This script contains code to support creation of source extractor-like and daophot-like sourcelists.

"""
import pdb
import sys


from astropy.io import fits
from astropy.stats import mad_std
import numpy as np
from photutils import aperture_photometry, CircularAperture, DAOStarFinder
from stsci.tools import logutil

from drizzlepac import util
from drizzlepac.hlautils import se_source_generation

__taskname__ = 'sourcelist_generation'

log = logutil.create_logger(__name__, level=logutil.logging.INFO, stream=sys.stdout)

# ----------------------------------------------------------------------------------------------------------------------


def create_dao_like_coordlists(fitsfile,sourcelist_filename,make_region_file=False,dao_fwhm=3.5,bkgsig_sf=2.):
    """Make daofind-like coordinate lists

    Parameters
    ----------
    fitsfile : string
        Name of the drizzle-combined filter product to used to generate photometric sourcelists.

    sourcelist_filename : string
        Name of optionally generated ds9-compatible region file

    dao_fwhm : float
        (photutils.DAOstarfinder param 'fwhm') The full-width half-maximum (FWHM) of the major axis of the
        Gaussian kernel in units of pixels. Default value = 3.5.

    make_region_file : Boolean
        Generate ds9-compatible region file? Default value = True

    bkgsig_sf : float
        multiplictive scale factor applied to background sigma value to compute DAOfind input parameter
        'threshold'. Default value = 2.

    Returns
    -------
    sources : astropy table
        Table containing x, y coordinates of identified sources
    """
    hdulist = fits.open(fitsfile)
    image = hdulist['SCI'].data
    image -= np.nanmedian(image)
    bkg_sigma = mad_std(image, ignore_nan=True)
    daofind = DAOStarFinder(fwhm=dao_fwhm, threshold=bkgsig_sf * bkg_sigma)
    sources = daofind(image)
    hdulist.close()

    for col in sources.colnames:
        sources[col].info.format = '%.8g'  # for consistent table output

    # Write out ecsv file
    tbl_length = len(sources)
    sources.write(sourcelist_filename, format="ascii.ecsv")
    log.info("Created coord list  file '{}' with {} sources".format(sourcelist_filename, tbl_length))

    if make_region_file:
        out_table = sources.copy()
        # Remove all other columns besides xcentroid and ycentroid
        out_table.keep_columns(['xcentroid','ycentroid'])

        # Add offset of 1.0 in X and Y to line up sources in region file with image displayed in ds9.
        out_table['xcentroid'].data[:] += np.float64(1.0)
        out_table['ycentroid'].data[:] += np.float64(1.0)

        reg_filename = sourcelist_filename.replace(".ecsv",".reg")
        out_table.write(reg_filename, format="ascii")
        log.info("Created region file '{}' with {} sources".format(reg_filename, len(out_table)))

    return(sources)


# ----------------------------------------------------------------------------------------------------------------------


def create_dao_like_sourcelists(fitsfile,sl_filename,sources,aper_radius=4.,make_region_file=False):
    """Make DAOphot-like sourcelists

    Parameters
    ----------
    fitsfile : string
        Name of the drizzle-combined filter product to used to generate photometric sourcelists.


    sl_filename : string
        Name of the sourcelist file that will be generated by this subroutine

    sources : astropy table
        Table containing x, y coordinates of identified sources

    aper_radius : float
        Aperture radius (in pixels) used for photometry. Default value = 4.

    make_region_file : Boolean
        Generate ds9-compatible region file(s) along with the sourcelist? Default value = False

    Returns
    -------
    Nothing.
    """
    # Open and background subtract image
    hdulist = fits.open(fitsfile)
    image = hdulist['SCI'].data
    image -= np.nanmedian(image)


    # Aperture Photometry
    positions = (sources['xcentroid'], sources['ycentroid'])
    apertures = CircularAperture(positions, r=aper_radius)
    phot_table = aperture_photometry(image, apertures)

    for col in phot_table.colnames: phot_table[col].info.format = '%.8g'  # for consistent table output
    hdulist.close()

    # Write out sourcelist
    tbl_length = len(phot_table)
    phot_table.write(sl_filename, format="ascii.ecsv")
    log.info("Created sourcelist file '{}' with {} sources".format(sl_filename, tbl_length))

    # Write out ds9-compatable .reg file
    if make_region_file:
        reg_filename = sl_filename.replace(".ecsv",".reg")
        out_table = phot_table.copy()
        out_table['xcenter'].data = out_table['xcenter'].data + np.float64(1.0)
        out_table['ycenter'].data = out_table['ycenter'].data + np.float64(1.0)
        out_table.remove_column('id')
        out_table.write(reg_filename, format="ascii")
        log.info("Created region file '{}' with {} sources".format(reg_filename, tbl_length))


# ----------------------------------------------------------------------------------------------------------------------


def create_sourcelists(obs_info_dict, param_dict):
    """Main calling code. Make sourcelists

    Parameters
    ----------
    obs_info_dict : dictionary
        Dictionary containing all information about the images being processed

    param_dict : dictionary
        Dictionary of instrument/detector - specific drizzle, source finding and photometric parameters

    Returns
    -------
    catalog_list : list
        List of filenames of all catalogs created
    """
    catalog_list = []

    log.info("-" * 118)
    for product_type in obs_info_dict:
        for item_type in obs_info_dict[product_type]:
            log.info("obs_info_dict[{}][{}]: {}".format(product_type, item_type, obs_info_dict[product_type][item_type]))  # TODO: REMOVE THIS SECTION BEFORE ACTUAL USE
    log.info("-" * 118)

    for tdp_keyname in [oid_key for oid_key in list(obs_info_dict.keys()) if
                        oid_key.startswith('total detection product')]:  # loop over total filtered products
        log.info("=====> {} <======".format(tdp_keyname))
        parse_tdp_info = obs_info_dict[tdp_keyname]['info'].split()
        inst_det = "{} {}".format(parse_tdp_info[2].upper(), parse_tdp_info[3].upper())

        detection_image = obs_info_dict[tdp_keyname]['product filenames']['image']
        tdp_seg_catalog_filename = obs_info_dict[tdp_keyname]['product filenames']['segment source catalog']
        tdp_ps_catalog_filename = obs_info_dict[tdp_keyname]['product filenames']['point source catalog']

        segmap, kernel, bkg_dao_rms = se_source_generation.create_sextractor_like_sourcelists(
            detection_image, tdp_seg_catalog_filename, param_dict[inst_det], se_debug=False)

        dao_coord_list = create_dao_like_coordlists(detection_image, tdp_ps_catalog_filename)
        catalog_list.append(tdp_seg_catalog_filename)
        catalog_list.append(tdp_ps_catalog_filename)

        for fp_keyname in obs_info_dict[tdp_keyname]['associated filter products']:
            filter_combined_imagename = obs_info_dict[fp_keyname]['product filenames']['image']

            point_source_catalog_name = obs_info_dict[fp_keyname]['product filenames']['point source catalog']
            seg_source_catalog_name = obs_info_dict[fp_keyname]['product filenames']['segment source catalog']

            log.info("Filter combined image... {}".format(filter_combined_imagename))
            log.info("Point source catalog.... {}".format(point_source_catalog_name))
            log.info("Segment source catalog.. {}".format(seg_source_catalog_name))

            se_source_generation.measure_source_properties(segmap, kernel, filter_combined_imagename,
                                                           seg_source_catalog_name, param_dict[inst_det])

            create_dao_like_sourcelists(filter_combined_imagename, point_source_catalog_name, dao_coord_list)
            catalog_list.append(seg_source_catalog_name)
            catalog_list.append(point_source_catalog_name)

    return catalog_list

# ----------------------------------------------------------------------------------------------------------------------


@util.with_logging
def run_create_sourcelists(obs_info_dict, param_dict):
    """ subroutine to run create_sourcelists and produce log file when not run sourcelist_generation is not run from
    hlaprocessing.py.

    Parameters
    ----------
    obs_info_dict : dictionary
        Dictionary containing all information about the images being processed

    param_dict : dictionary
        Dictionary of instrument/detector - specific drizzle, source finding and photometric parameters

    Returns
    -------
    """

    catalog_list = create_sourcelists(obs_info_dict, param_dict)
