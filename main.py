from netCDF4 import Dataset
import numpy as np
import pandas as pd
import time as t
import argparse


def make_ozone_netcdf(in_file, out_file = 'ozone_box_interview_data.nc', skiprows = 5, expected_format = True):
    """
    Takes CSV file provided for NCAS interview and converts into netCDF.
    Input options
     in_file         - string. Input CSV file. Required.
     out_file        - string. Name of output CSV file. Default ozone_box_interview_data.
     skiprows        - integer. Number of rows at top of csv before headers for data. 
                         Data in top rows used for attributes, see expected_format below. Default 5.
     expected_format - bool. If top rows are in expected format, use data for global attributes.
                         Expected format is: top row - instrument name, second row - contact name, 
                                             third row - description, fourth row - creator.
                         If false, attributes are ommited with the exception of a default title, 
                         Ozone Concentration Data. Default true.
    Output
     netcdf file, written to out_file.
    """
    # open file to get data at top of file
    with open(in_file, 'r') as f:
        header = [next(f).strip('\n') for x in range(skiprows)]

    # read rest of file to pandas dataframe, convert time to seconds past midnight
    df = pd.read_csv(in_file, skiprows = skiprows)
    df['Time (UTC)'] = pd.to_datetime(df['Time (UTC)'], utc = True, dayfirst = True, infer_datetime_format=True)
    seconds = [((h.hour * 3600) + (h.minute * 60) + (h.second)) for h in df['Time (UTC)']]
    df = df.assign(seconds_past_midnight=seconds)

    # get data start and end dates and times
    start_data_date = df['Time (UTC)'][0].strftime('%Y-%m-%d')
    start_data_time = df['Time (UTC)'][0].strftime('%H:%M:%S')
    end_data_date = df['Time (UTC)'].iloc[-1].strftime('%Y-%m-%d')
    end_data_time = df['Time (UTC)'].iloc[-1].strftime('%H:%M:%S')

    # get quality control values and meanings
    qc_vals = sorted(set(df['Quality Control Falg Value']))
    qc_meanings = []
    for val in qc_vals:
        val_index = df.loc[df['Quality Control Falg Value'] == val].index[0]
        qc_meanings.append(df['Quality Control Flag Meaning'][val_index].replace(' ','_'))

    # create netcdf file, add global attributes
    nc_file = Dataset(out_file, 'w', format='NETCDF4_CLASSIC')
    if expected_format:
        nc_file.title = f'{header[0]} Data'
        nc_file.instrument_name = header[0]
        nc_file.contact = header[1]
        nc_file.description = header[2]
        nc_file.creator = header[3]
    else:
        nc_file.title = 'Ozone Concentration Data'
    nc_file.history = f"Created at {t.strftime('%Y-%m-%d %H:%M:%S')}"
    nc_file.start_time = f'{start_data_date} {start_data_time}Z'
    nc_file.end_time = f'{end_data_date} {end_data_time}Z'

    # create dimensions, only Time exists
    nc_file.createDimension('time', None)

    # create variables
    time = nc_file.createVariable('time', 'f8', ('time',))
    time.units = f'seconds since {start_data_date} 00:00:00 +00:00'

    ozone_concentration = nc_file.createVariable('ozone_concentration', 'f4', ('time',))
    ozone_concentration.long_name = 'ozone concentration'
    ozone_concentration.units = "parts per billion"
    
    quality_control = nc_file.createVariable('qc_flag', 'i4', ('time',))
    quality_control.long_name = 'quality control flag'
    quality_control.flag_values = qc_vals
    quality_control.flag_meanings = ' '.join(qc_meanings)

    # add data to variables
    time[:] = df['seconds_past_midnight']
    ozone_concentration[:] = df['Ozone Concentration (ppb)']
    quality_control[:] = df['Quality Control Falg Value']

    # close file
    nc_file.close()


if __name__ == "__main__":
    # if script run from command line, parse options and make netcdf file
    parser = argparse.ArgumentParser(description='Convert csv file to netcdf file.')
    parser.add_argument('input_file', type = str, help = 'Name of CSV file to convert')
    parser.add_argument('-o', '--outfile', type = str, default = 'ozone_box_interview_data.nc', help = 'Name of netCDF file to be created. Default is ozone_box_interview_data.nc')
    parser.add_argument('-s', '--skiprows', type = int, default = 5, help = 'Number of rows in input file to skip before data headers. Default = 5')
    args = parser.parse_args()
    make_ozone_netcdf(args.input_file, out_file = args.outfile, skiprows = args.skiprows)
