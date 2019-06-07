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

__taskname__ = 'sourcelist_generation'

log = logutil.create_logger(__name__, level=logutil.logging.INFO, stream=sys.stdout)

# ----------------------------------------------------------------------------------------------------------------------


def create_dao_like_coordlists(fitsfile,dao_fwhm=3.5,bkgsig_sf=2.):
    """Make daofind-like coordinate lists

    Parameters
    ----------
    fitsfile : string
        Name of the drizzle-combined filter product to used to generate photometric sourcelists.

    dao_fwhm : float
        (photutils.DAOstarfinder param 'fwhm') The full-width half-maximum (FWHM) of the major axis of the
        Gaussian kernel in units of pixels. Default value = 3.5.

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
    return(sources)


# ----------------------------------------------------------------------------------------------------------------------


def create_dao_like_sourcelists(fitsfile,sl_filename,sources,aper_radius=4.):
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

    # Write out preliminary sourcelist
    out_table = phot_table.copy()
    out_table['xcenter'].data = out_table['xcenter'].data + np.float64(1.0)
    out_table['ycenter'].data = out_table['ycenter'].data + np.float64(1.0)
    out_table.remove_column('id')
    out_table.write(sl_filename, format="ascii")
    log.info("Created catalog '{}' with {} sources".format(sl_filename, len(out_table)))

# ----------------------------------------------------------------------------------------------------------------------


def create_se_like_coordlists():
    """Make source extractor-like coordinate lists

    Parameters
    ----------

    Returns
    -------
    """

    log.info("SOURCE EXTRACTOR-LIKE COORDINATE LIST CREATION OCCURS HERE!")


# ----------------------------------------------------------------------------------------------------------------------


def create_se_like_sourcelists():
    """Make source extractor-like sourcelists

    Parameters
    ----------

    Returns
    -------
    """

    log.info("SOURCE EXTRACTOR-LIKE SOURCELIST CREATION OCCURS HERE!")


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
    """
    log.info("-" * 118)
    for product_type in obs_info_dict:
        for key2 in list(obs_info_dict[key1].keys()):
            log.info("obs_info_dict[{}][{}]: {}".format(key1,key2,obs_info_dict[key1][key2]))  # TODO: REMOVE THIS SECTION BEFORE ACTUAL USE
    log.info("-"*118)

    for tdp_keyname in [oid_key for oid_key in list(obs_info_dict.keys()) if
                        oid_key.startswith('total detection product')]:  # loop over total filtered products
        log.info("=====> {} <======".format(tdp_keyname))
        # 0: Map image filename to correspoinding catalog filename for total detection product and the associated
        # filter products
        totdet_product_cat_dict = {}
        filter_product_cat_dict = {}
        filter_component_dict = {}
        totdet_product_cat_dict[obs_info_dict[tdp_keyname]['product filenames']['image']] = \
            obs_info_dict[tdp_keyname]['product filenames']['source catalog']
        for fp_keyname in obs_info_dict[tdp_keyname]['associated filter products']:
            filter_product_cat_dict[obs_info_dict[fp_keyname]['product filenames']['image']] = \
                obs_info_dict[fp_keyname]['product filenames']['source catalog']
            filter_component_dict[obs_info_dict['filter product 00']['info'].split()[-1].lower()] = \
                obs_info_dict[fp_keyname]['files']

        create_se_like_coordlists()
        dao_coord_list = create_dao_like_coordlists(obs_info_dict[tdp_keyname]['product filenames']['image'])

        for filter_img in filter_product_cat_dict.keys():
            create_se_like_sourcelists()

            create_dao_like_sourcelists(filter_img,filter_product_cat_dict[filter_img],dao_coord_list)
            

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

    create_sourcelists(obs_info_dict, param_dict)


