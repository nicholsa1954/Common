import io
import pandas as pd
from nextcloud import NextCloud

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

def InitializeNextCloudDataFrames(path, data_file, remote_file = False):
    
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    # if not Path(path).exists():
    #     print("Can't find the path:", path,'-- returning empty DataFrame.')
    #     print('Do you need to enter network credentials?')
    #     return pd.DataFrame()
    
    
    with NextCloud(
        NEXTCLOUD_URL,
        user = NEXTCLOUD_USERNAME,
        password = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            }) as nxc:
    
        data_file = nxc.get_file(''.join([path, data_file]))
        data_bytes_io = io.BytesIO(data_file.fetch_file_content())
        data_bytes_io.seek(0)
        return pd.read_excel(data_bytes_io, engine='openpyxl')