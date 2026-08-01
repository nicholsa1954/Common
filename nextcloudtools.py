import io
import asyncio
import pandas as pd
from nc_py_api import AsyncNextcloud

import sys
sys.path.append('./')
from testVPNConnection import testVPNConnection

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

async def InitializeNextCloudDataFrame(path, data_file, remote_file = False):
    
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    
    nxc = AsyncNextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            }) 
    
    data_file = await nxc.files.download(''.join([path, data_file]))
    data_bytes_io = io.BytesIO(data_file)
    data_bytes_io.seek(0)
    return pd.read_excel(data_bytes_io, engine='openpyxl')

async def InitializeNextCloudDataFramesDict(remote_path, data_file, remote_file = False):
    
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    
    nxc = AsyncNextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            }) 
    
    
    data_file = await nxc.files.download(''.join([remote_path, data_file]))
    data_bytes_io = io.BytesIO(data_file)
    data_bytes_io.seek(0)
    return pd.read_excel(data_bytes_io, sheet_name=None, engine='openpyxl')

async def UploadDfListToNextCloud(remote_filename, df_list, sheet_names, overwrite = True):

    buf = io.BytesIO()
    with pd.ExcelWriter(buf,  engine='openpyxl') as writer:
        buf.seek(0)
        for df, sheet_name in zip(df_list, sheet_names):
            copy = df.copy(deep = True)
            print(f'Starting sheet {sheet_name} ...') 
            if 'Timestamp' in copy.columns:
                copy['Timestamp'] = copy['Timestamp'].apply(lambda x: str(x))
                assert copy['Timestamp'].dtype =='object', 'failed to convert timestamp'
            copy.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print('Uploading to NextCloud...')
    nxc = Nextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD)

    buf.seek(0)
    result = await nxc.files.upload_stream(
        path = remote_filename,
        fp = buf,
        kwargs={'overwrite': overwrite, 
            'chunk_size': 10*1024*1024})

    return result


async def WriteMailingListToNextCloud(remote_filename, email_list, overwrite = True):
    buf = io.BytesIO()
    for email in sorted(email_list):
        buf.write(''.join([email,'\n']).encode('utf-8'))
    buf.seek(0)
    
    nxc = AsyncNextcloud(
        nextcloud_url = NEXTCLOUD_URL,
        nc_auth_user = NEXTCLOUD_USERNAME,
        nc_auth_pass = NEXTCLOUD_PASSWORD,
        session_kwargs ={
            'verify': True  # verify ssl
            })     

    result = await nxc.files.upload_stream(
        path = remote_filename,
        fp = buf,
        kwargs={'overwrite': overwrite, 
            'chunk_size': 10*1024*1024})   
    
    return result 


async def ReadFileListFromNextCloud(subdir = 'Shared/'):
    nxc = AsyncNextcloud(
    nextcloud_url = NEXTCLOUD_URL,
    nc_auth_user = NEXTCLOUD_USERNAME,
    nc_auth_pass = NEXTCLOUD_PASSWORD)
    
    file_list = []
    all_files = [i for i in await nxc.files.listdir(depth=-1) if not i.is_dir and i.user_path.startswith(subdir)]
    for obj in all_files:
        file_list.append(obj.user_path)
        
    return file_list