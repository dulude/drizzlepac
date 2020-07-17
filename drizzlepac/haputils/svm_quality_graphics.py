"""Code that evaluates the quality of the SVM products generated by the drizzlepac package.

The JSON files generated here can be converted directly into a Pandas DataFrame
using the syntax:

>>> import json
>>> import pandas as pd
>>> with open("<rootname>_astrometry_resids.json") as jfile:
>>>     resids = json.load(jfile)
>>> pdtab = pd.DataFrame(resids)

These DataFrames can then be concatenated using:

>>> allpd = pdtab.concat([pdtab2, pdtab3])

where 'pdtab2' and 'pdtab3' are DataFrames generated from other datasets.  For
more information on how to merge DataFrames, see

https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html

Visualization of these Pandas DataFrames with Bokeh can follow the example
from:

https://programminghistorian.org/en/lessons/visualizing-with-bokeh

"""

# Standard library imports
import argparse
import collections
from datetime import datetime
import glob
import json
import logging
import os
import pdb
import pickle
import re
import sys
import time

# Related third party imports
from astropy.coordinates import SkyCoord
from astropy.io import ascii, fits
from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from itertools import chain
import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from bokeh.layouts import row, column, gridplot
from bokeh.plotting import figure, output_file, save, show
from bokeh.models import ColumnDataSource, Label, CDSView
from bokeh.models.tools import HoverTool

# Local application imports
from drizzlepac import util, wcs_functions
import drizzlepac.devutils.comparison_tools.compare_sourcelists as csl
from drizzlepac.haputils.graph_utils import HAPFigure, build_tooltips
from drizzlepac.haputils.pandas_utils import PandasDFReader
from drizzlepac.devutils.comparison_tools.read_hla import read_hla_catalog
from stsci.tools import logutil
from stwcs import wcsutil
from stwcs.wcsutil import HSTWCS


__taskname__ = 'svm_quality_graphics'

MSG_DATEFMT = '%Y%j%H%M%S'
SPLUNK_MSG_FORMAT = '%(asctime)s %(levelname)s src=%(name)s- %(message)s'
log = logutil.create_logger(__name__, level=logutil.logging.NOTSET, stream=sys.stdout,
                            format=SPLUNK_MSG_FORMAT, datefmt=MSG_DATEFMT)
# ----------------------------------------------------------------------------------------------------------------------
# Module level variables

# ====================================================================================
# GAIA plots: number of GAIA sources, mean distance to neighbors, centroid/offset/std
# of sources in field
# ====================================================================================


def build_svm_plots(data_source, output_basename='', display_plot=False):
    """Create all the plots for the results generated by these comparisons

    Parameters
    ----------
    data_source : str
        Filename for master data file which contains all the results.  This will
        typically be an HSF5 file generated by the JSON harvester.

    output_base_filename : str
        Base name for the HMTL file generated by Bokeh.

    display_plot : bool
        Option to display the plot to the screen
        Default: False

    """
    if output_basename == '':
        output_basename = "svm_qa"
    else:
        output_basename = "{}_svm_qa".format(output_basename)

    # Column names as defined in the harvester dataframe mapped to simple names for ease of use
    gaia_col_names = {'distribution_characterization_statistics.Number_of_GAIA_sources': 'num_GAIA',
                      'distribution_characterization_statistics.X_centroid': 'x_centroid',
                      'distribution_characterization_statistics.X_offset': 'x_offset',
                      'distribution_characterization_statistics.X_standard_deviation': 'x_std',
                      'distribution_characterization_statistics.Y_centroid': 'y_centroid',
                      'distribution_characterization_statistics.Y_offset': 'y_offset',
                      'distribution_characterization_statistics.Y_standard_deviation': 'y_std',
                      'distribution_characterization_statistics.maximum_neighbor_distance': 'max_neighbor_dist',
                      'distribution_characterization_statistics.mean_neighbor_distance': 'mean_neighbor_dist',
                      'distribution_characterization_statistics.minimum_neighbor_distance': 'min_neighbor_dist',
                      'distribution_characterization_statistics.standard_deviation_of_neighbor_distances': 'std_neighbor_dist'}

    # Get the requested columns from the dataframe in addition columns
    # added by the pandas_utils
    gaia_cols_DF = get_pandas_data(data_source, gaia_col_names)

    # Rename the columns to abbreviated text for ease of management
    for old_col_name, new_col_name in gaia_col_names.items():
        gaia_cols_DF.rename(columns={old_col_name: new_col_name}, inplace=True)

    gaia_plots_name = build_gaia_plots(gaia_cols_DF, list(gaia_col_names.values()), display_plot,
                                       output_basename=output_basename)

    #     -      -     -      -     -      -     -      -     -      -     -      -     -      -     -      -
    # Generate plots for interfilter cross-match comparisons
    # Column names as defined in the harvester dataframe mapped to simple names for ease of use
    intfilt_xm_col_names = {'Interfilter_cross-match_details.reference_catalog_filename': 'ref_catalog_filename',
                            'Interfilter_cross-match_details.comparison_catalog_filename': 'comp_catalog_filename',
                            'Interfilter_cross-match_details.reference_catalog_length': 'ref_catalog_length',
                            'Interfilter_cross-match_details.comparison_catalog_length': 'comp_catalog_length',
                            'Interfilter_cross-match_details.number_of_cross-matches': 'number_of_cross-matches',
                            'Interfilter_cross-match_details.percent_of_all_identified_reference_sources_crossmatched': 'ref_crossmatch_percentage',
                            'Interfilter_cross-match_details.percent_of_all_identified_comparison_sources_crossmatched': 'comp_crossmatch_percentage',
                            'Interfilter_cross-match_details.reference_image_platescale': 'ref_image_platescale',
                            'Interfilter_cross-matched_reference_catalog.xcentroid_ref': 'ref_catalog.xcentroid_ref',
                            'Interfilter_cross-matched_reference_catalog.ycentroid_ref': 'ref_catalog.ycentroid_ref',
                            'Interfilter_cross-matched_comparison_catalog.xcentroid_ref': 'comp_catalog.xcentroid_ref',
                            'Interfilter_cross-matched_comparison_catalog.ycentroid_ref': 'comp_catalog.ycentroid_ref',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_min': 'x_non-clipped_min',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_max': 'x_non-clipped_max',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_mean': 'x_non-clipped_mean',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_median': 'x_non-clipped_median',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_standard_deviation': 'x_non-clipped_rms',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_mean': 'x_3x3_sigma-clipped_mean',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_median': 'x_3x3_sigma-clipped_median',
                            'Interfilter_cross-matched_xcentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_standard_deviation': 'x_3x3_sigma-clipped_rms',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_min': 'y_non-clipped_min',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_max': 'y_non-clipped_max',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_mean': 'y_non-clipped_mean',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_median': 'y_non-clipped_median',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.Non-clipped_standard_deviation': 'y_non-clipped_rms',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_mean': 'y_3x3_sigma-clipped_mean',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_median': 'y_3x3_sigma-clipped_median',
                            'Interfilter_cross-matched_ycentroid_ref_comparison_-_reference_separation_statistics.3x3_sigma-clipped_standard_deviation': 'y_3x3_sigma-clipped_rms',
                            'Interfilter_cross-matched_comparison_-_reference_separations.delta_xcentroid_ref': 'comp-ref_x_seperation',
                            'Interfilter_cross-matched_comparison_-_reference_separations.delta_ycentroid_ref': 'comp-ref_y_seperation'}

    # Get the requested columns from the dataframe in addition columns
    # added by the pandas_utils
    if_xm_DF = get_pandas_data(data_source, intfilt_xm_col_names)

    # Rename the columns to abbreviated text for ease of management
    for old_col_name, new_col_name in intfilt_xm_col_names.items():
        if_xm_DF.rename(columns={old_col_name: new_col_name}, inplace=True)

    # remove rows that aren't relevant
    if_xm_DF = if_xm_DF[np.isnan(if_xm_DF.ref_image_platescale) == False]

    # make the interfilter cross match plots
    if_xm_plots_name = build_interfilter_crossmatch_plots(if_xm_DF, list(intfilt_xm_col_names.values()),
                                                          display_plot, output_basename=output_basename)

    #     -      -     -      -     -      -     -      -     -      -     -      -     -      -     -      -
    # Generate plots for point-segment catalog cross-match comparisons
    """
    xmatch_col_names = {'Cross-match_details.number_of_cross-matches',
                                       'Cross-match_details.point_catalog_filename',
                                       'Cross-match_details.point_catalog_length',
                                       'Cross-match_details.point_frame',
                                       'Cross-match_details.segment_catalog_filename',
                                       'Cross-match_details.segment_catalog_length',
                                       'Cross-match_details.segment_frame',
                                       'Cross-matched_point_catalog.Declination',
                                       'Cross-matched_point_catalog.Right ascension',
                                       'Cross-matched_segment_catalog.Declination',
                                       'Cross-matched_segment_catalog.Right ascension',
                                       'Segment_-_point_on-sky_separation_statistics.3x3_sigma-clipped_mean',
                                       'Segment_-_point_on-sky_separation_statistics.3x3_sigma-clipped_median',
                                       'Segment_-_point_on-sky_separation_statistics.3x3_sigma-clipped_standard_deviation',
                                       'Segment_-_point_on-sky_separation_statistics.Non-clipped_max',
                                       'Segment_-_point_on-sky_separation_statistics.Non-clipped_mean',
                                       'Segment_-_point_on-sky_separation_statistics.Non-clipped_median',
                                       'Segment_-_point_on-sky_separation_statistics.Non-clipped_min',
                                       'Segment_-_point_on-sky_separation_statistics.Non-clipped_standard_deviation']

    #xmatch_cols = get_pandas_data(data_source, xmatch_col_names)

    #xmatch_plots_name = build_crossmatch_plots(xmatch_cols, xmatch_col_names,
    #                              output_basename=output_basename)
    """


# -----------------------------------------------------------------------------
# Functions for generating each data plot
#
def build_gaia_plots(gaiaDF, data_cols, display_plot, output_basename='svm_qa'):
    """
    Generate the plots for evaluating the distribution of GAIA catalog sources
    in the field-of-view of each product.

    Parameters
    ----------
    gaiaDF : Pandas dataframe
        This dataframe contains all the columns relevant to the plots.

    data_cols : list
        A subset of the column names in gaiaDF

    output_basename : str
        String to use as the start of the filename for the output plot pages.

    display_plot : bool
        Option to display the plot in addition to writing out the file.

    Returns
    -------
    output : str
        Name of HTML file where the plot was saved.

    """
    # Setup the source of the data to be plotted so the axis variables can be
    # referenced by column name in the Pandas dataframe
    gaiaCDS = ColumnDataSource(gaiaDF)
    num_of_datasets = len(gaiaCDS.data['index'])
    print('Number of datasets: {}'.format(num_of_datasets))

    output_basename = "{}_gaia_comparison".format(output_basename)

    if not output_basename.endswith('.html'):
        output = output_basename + '.html'
    else:
        output = output_basename
    # Set the output file immediately as advised by Bokeh.
    output_file(output)

    # Generate the graphic-specific tooltips - be mindful of
    # the default tooltips defined in graph_utils.py
    gaia_tooltips_list = ['DATE', 'RA', 'DEC', 'GYRO', 'EXPTIME',
                          'ALIGNED_TO']

    gaia_hover_columns = ['header.DATE-OBS',
                          'header.RA_TARG',
                          'header.DEC_TARG',
                          'header.GYROMODE',
                          'header.EXPTIME',
                          'fit_results.aligned_to']

    gaia_tips = build_tooltips(gaia_tooltips_list, gaia_hover_columns, list(range(0, len(gaia_hover_columns))))
    #
    # Define the graphics
    #

    # Scatter figures
    p0 = HAPFigure(title='Centroid of GAIA Sources in Field',
                   x_label='X Centroid (pixels)',
                   y_label='Y Centroid (pixels)',
                   hover_tips=gaia_tips)
    p0.build_glyph('circle',
                   x='x_centroid',
                   y='y_centroid',
                   sourceCDS=gaiaCDS,
                   glyph_color='colormap',
                   legend_group='inst_det')

    p1 = HAPFigure(title='Offset of Centroid of GAIA Sources in Field',
                   x_label='X Offset (pixels)',
                   y_label='Y Offset (pixels)',
                   hover_tips=gaia_tips)
    p1.build_glyph('circle',
                   x='x_offset',
                   y='y_offset',
                   sourceCDS=gaiaCDS,
                   glyph_color='colormap',
                   legend_group='inst_det')

    p2 = HAPFigure(title='Standard Deviation of GAIA Source Positions in Field',
                   x_label='STD(X) (pixels)',
                   y_label='STD(Y) (pixels)',
                   hover_tips=gaia_tips)
    p2.build_glyph('circle',
                   x='x_std',
                   y='y_std',
                   sourceCDS=gaiaCDS,
                   glyph_color='colormap',
                   legend_group='inst_det')

    # Histogram figures
    """
    p3 = HAPFigure(title='Mean distance between GAIA sources in Field',
                   xlabel='Separation (pixels)',
                   ylabel='Number of products',
                   use_hover_tips=False,
                   background_fill_color='gainsboro',
                   toolbar_location='right',
                   ystart=0,
                   grid_line_color='white')
    mean_dist = gaiaDF.loc[:, 'mean_neighbor_dist'].dropna()
    hist3, edges3 = np.histogram(mean_dist, bins=50)
    p3.build_histogram(top=hist3,
                       bottom=0,
                       left=edges3[:-1],
                       right=edges3[1:],
                       fill_color='navy',
                       fill_transparency=0.5,
                       line_color='white')
    """

    p4 = HAPFigure(title='Number of GAIA sources in Field',
                   xlabel='Number of GAIA sources',
                   ylabel='Number of products',
                   use_hover_tips=False,
                   background_fill_color='gainsboro',
                   toolbar_location='right',
                   ystart=0,
                   grid_line_color='white')
    num_of_GAIA_sources = gaiaDF.loc[:, 'num_GAIA'].dropna()
    hist4, edges4 = np.histogram(num_of_GAIA_sources, bins=50)
    p4.build_histogram(top=hist4,
                       bottom=0,
                       left=edges4[:-1],
                       right=edges4[1:],
                       fill_color='navy',
                       fill_transparency=0.5,
                       line_color='white')

    # Display and save
    if display_plot:
        show(column(p4.fig, p0.fig, p1.fig, p2.fig))
        # show(column(p4.fig, p0.fig, p1.fig, p2.fig, p3.fig))
    # Just save
    else:
        save(column(p4.fig, p0.fig, p1.fig, p2.fig))
        # save(column(p4.fig, p0.fig, p1.fig, p2.fig, p3.fig))
    log.info("Output HTML graphic file {} has been written.\n".format(output))

    # Return the name of the plot layout file just created
    return output


"""
def build_crossmatch_plots(xmatchCDS, data_cols, output_basename='svm_qa'):
    Generate the cross-match statistics plots for the comparison between the
    point catalog and the segment catalog.

    Parameters
    ----------
    xmatchCDS : Pandas ColumnDataSource
        This object contains all the columns relevant to the cross-match plots.

    data_cols : list
        The list of column names for the columns read in to the `xmatchCDS` object.

    output_basename : str
        String to use as the start of the filename for the output plot pages.

    Returns
    -------
    output : str
        Name of HTML file where the plot was saved.

    output_basename = "{}_crossmatch_comparison".format(output_basename)

    if not output_basename.endswith('.html'):
        output = output_basename + '.html'
    else:
        output = output_basename
    # Set the output file immediately as advised by Bokeh.
    output_file(output)

    num_hover_cols = len(HOVER_COLUMNS)

    colormap = [qa.DETECTOR_LEGEND[x] for x in xmatchCDS.data[data_cols[1]]]
    xmatchCDS.data['colormap'] = colormap
    inst_det = ["{}/{}".format(i,d) for (i,d) in zip(xmatchCDS.data[data_cols[0]],
                                         xmatchCDS.data[data_cols[1]])]
    xmatchCDS.data[qa.INSTRUMENT_COLUMN] = inst_det

    plot_list = []

    hist0, edges0 = np.histogram(xmatchCDS.data[data_cols[num_hover_cols]], bins=50)
    title0 = 'Number of Point-to-Segment Cross-matched sources'
    p0 = [plot_histogram(title0, hist0, edges0, y_start=0, '#fafafa',
                    xlabel='Number of Cross-matched sources', ylabel='Number of products')]
    plot_list += p0

    hist1, edges1 = np.histogram(xmatchCDS.data[data_cols[num_hover_cols + 11]], bins=50)
    title1 = 'Mean Separation (Sigma-clipped) of Point-to-Segment Cross-matched sources'
    p1 = [plot_histogram(title1, hist1, edges1, y_start=0,
                    fill_color='navy', background_fill_color='#fafafa',
                    xlabel='Mean Separation of Cross-matched sources (arcseconds)', ylabel='Number of products')]
    plot_list += p1

    hist2, edges2 = np.histogram(xmatchCDS.data[data_cols[num_hover_cols + 12]], bins=50)
    title2 = 'Median Separation (Sigma-clipped) of Point-to-Segment Cross-matched sources'
    p2 = [plot_histogram(title2, hist2, edges2, y_start=0,
                    fill_color='navy', background_fill_color='#fafafa',
                    xlabel='Median Separation of Cross-matched sources (arcseconds)', ylabel='Number of products')]
    plot_list += p2

    hist3, edges3 = np.histogram(xmatchCDS.data[data_cols[num_hover_cols + 13]], bins=50)
    title3 = 'Standard-deviation (sigma-clipped) of Separation of Point-to-Segment Cross-matched sources'
    p3 = [plot_histogram(title3, hist3, edges3, y_start=0,
                    fill_color='navy', background_fill_color='#fafafa',
                    xlabel='STD(Separation) of Cross-matched sources (arcseconds)', ylabel='Number of products')]
    plot_list += p3

    # Save the plot to an HTML file
    save(column(plot_list))

    return output
"""

def build_interfilter_crossmatch_plots(xm_df, data_cols, display_plot, output_basename='svm_qa'):
    """"Generate plots to statiscially quantify the quality of the alignment of filter-level HAP imagery
    products

    Parameters
    ----------
    xm_df : Pandas dataframe
        This dataframe contains all the columns relevant to the plots.

    data_cols : list
        A subset of the column names in gaiaDF

    output_basename : str
        String to use as the start of the filename for the output plot pages.

    display_plot : bool
        Option to display the plot in addition to writing out the file.

    Returns
    -------
    output : str
        Name of HTML file where the plot was saved.
    """
    # Setup the source of the data to be plotted so the axis variables can be
    # referenced by column name in the Pandas dataframe
    xm_cds = ColumnDataSource(xm_df)
    num_of_datasets = len(xm_cds.data['index'])
    print('Number of datasets: {}'.format(num_of_datasets))

    output_basename = "{}_interfilter_crossmatch_comparison".format(output_basename)

    if not output_basename.endswith('.html'):
        output = output_basename + '.html'
    else:
        output = output_basename
    # Set the output file immediately as advised by Bokeh.
    output_file(output)


    plots = []
    # plot #1: comp vs ref percent of all identified sources that were crossmatched
    plot = make_scatter_plot(xm_cds,
                             'Percentage of all identified sources matched',
                             '% of all reference sources crossmatched',
                             '% of all comparison sources crossmatched',
                             'ref_crossmatch_percentage',
                             'comp_crossmatch_percentage')
    plots.append(plot.fig)

    # 2: delta_X vs delta_Y vector plot for each cross-matched filter and/or x vs delta_x, x vs. delta_y, y vs. delta_x, y vs. delta_y quad plot each cross-matched filter
    # 3: Non-clipped min: plot x vs y values for all filters

    # 4: Non-clipped max: plot x vs y values for all filters
    # 5: Non-clipped mean: plot x vs y values for all filters
    # 6: Non-clipped median: plot x vs y values for all filters
    # 7: Non-clipped standard deviation: plot x vs y values for all filters
    # 8: 3x3 sigma-clipped mean: plot x vs y values for all filters
    # 9: 3x3 sigma-clipped median: plot x vs y values for all filters
    # 10: 3x3 sigma-clipped standard deviation: plot x vs y values for all filters

    if display_plot:
        show(column(plots))
    # Just save
    else:
        save(column(plots))
    log.info("Output HTML graphic file {} has been written.\n".format(output))


# -----------------------------------------------------------------------------
# Utility functions for plotting
#


def get_pandas_data(data_source, data_columns):
    """Load the harvested data, stored in a CSV file, into local arrays.

    Parameters
    ==========
    data_source : str
        Name of the file containing the Pandas Dataframe created by the harvester.

    data_columns : dict of str
        Column names from the Pandas dataframe mapped to simple names

    Returns
    =======
    data_colsDF : Pandas dataframe
    Dataframe which is a subset of the input harvester Pandas dataframe.
    The subset dataframe consists of only the requested columns.

    """

    # Instantiate a Pandas Dataframe Reader (lazy instantiation)
    df_handle = PandasDFReader(data_source, log_level=logutil.logging.NOTSET)

    # Get the relevant column data
    data_colsDF = df_handle.get_columns_HDF5(data_columns)

    return data_colsDF


def make_scatter_plot(xm_cds, title, x_label, y_label, x_data_colname, y_data_colname):
    """create a basic scatter plot

        Parameters
    ----------
    cds : Pandas dataframe
        This dataframe contains all the columns relevant to the plots.

    title : str
        plot title

    x_label : str
        X-axis label

    y_label : str
        Y-axis label

    x_data_colname : str
        **cds** data element to plot on the X axis

     y_data_colname : str
        **cds** data element to plot on the y axis

    Returns
    -------
    scatter_plot :

    """
    scatterplot = HAPFigure(title=title, x_label=x_label, y_label=y_label)#, hover_tips=gaia_tips)
    scatterplot.build_glyph('circle',
                            x=x_data_colname,
                            y=y_data_colname,
                            sourceCDS=xm_cds,
                            glyph_color='colormap',
                            legend_group='inst_det')
    return scatterplot

if __name__ == "__main__":
    build_svm_plots(sys.argv[1], output_basename='', display_plot=True)