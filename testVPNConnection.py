
import subprocess

host = "192.168.113.1"
def testVPNConnection():
    ping = subprocess.Popen(["ping.exe","-n","1","-w","1",host],stdout = subprocess.PIPE).communicate()[0]
    if ('unreachable' in str(ping)) or ('timed' in str(ping)) or ('failure' in str(ping)):
        print('Connection failed -- VPN is not connected.')
        print('ping returns:', str(ping))
        return False
    else:
        print("VPN is connected...")
        return True    
