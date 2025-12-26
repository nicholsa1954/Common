import io
import pandas as pd
from nc_py_api import Nextcloud

import sys
sys.path.append('./')
from testVPNConnection import testVPNConnection
from pathlib import Path

import configparser
config = configparser.ConfigParser()
config.read('../../Keys/config.ini')

NEXTCLOUD_URL = config['NextCloud']['url']
NEXTCLOUD_USERNAME = config['NextCloud']['username']
NEXTCLOUD_PASSWORD = config['NextCloud']['password']

import certifi
import urllib3

http = urllib3.PoolManager(
    cert_reqs="CERT_REQUIRED",
    ca_certs=certifi.where()
)

def InitializeNextCloudDataFrame(path, data_file, remote_file = False):
    
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    
    nxc = Nextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            }) 
    
    data_file = nxc.files.download(''.join([path, data_file]))
    data_bytes_io = io.BytesIO(data_file)
    data_bytes_io.seek(0)
    return pd.read_excel(data_bytes_io, engine='openpyxl')

def InitializeNextCloudDataFramesDict(remote_path, data_file, remote_file = False):
    
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    
    nxc = Nextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            }) 
    
    
    data_file = nxc.files.download(''.join([remote_path, data_file]))
    data_bytes_io = io.BytesIO(data_file)
    data_bytes_io.seek(0)
    return pd.read_excel(data_bytes_io, sheet_name=None, engine='openpyxl')

def UploadDfToNextCloud(df, remote_path, remote_filename, overwrite = True):

    nxc = Nextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD)
    
    data_bytes_io = io.BytesIO()

    remote_file_path = ''.join([remote_path, remote_filename])    
    with pd.ExcelWriter(data_bytes_io, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    data_bytes_io.seek(0)
    result = nxc.files.upload_stream(
        path = remote_file_path,
        fp = data_bytes_io,
        overwrite = overwrite
    )
    return result