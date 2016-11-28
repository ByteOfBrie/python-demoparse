import struct
import socket
 
class DemoInfo():
    def __init__(self):
        self.dem_prot = None        # demo protocol version 
        self.net_prot = None        # network protocol versio
        self.host_name = None       # HOSTNAME in case of TV, and IP:PORT or localhost:PORT in case of record in eyes
        self.client_name = None     # client name or TV name
        self.map_name = None        # map name
        self.gamedir = None         # root game directory
        self.time = None            # playback time (s)
        self.ticks = None           # number of ticks
        self.frames = None          # number of frames
        self.tickrate = None        # tickrate
        self.demo_type = None       # 0=record in eye, 1 = TV
        self.status_present = None  # true if a status command is available in the demo

def readStr(demo_file, n=260):
    return demo_file.read(n).decode('utf-8').strip('\x00')

def readInt(demo_file, n=4):
    val = struct.unpack('=i', demo_file.read(n))[0]
    return val

def readFloat(demo_file, n=4):
    return struct.unpack('=f', demo_file.read(n))[0]
 
def IsGoodIPPORTFormat(ip_str):
    '''check for valid ip adress, does not need to be perfect'''
    ip_str = ip_str.replace('localhost', '127.0.0.1')
    try:
        socket.inet_aton(ip_str)
        return True
    except socket.error:
        return False
 
def getDemoInfo(pathtofile, fast = False): # BOOL fast : if true, doesn't check the presence of the status 
    infos = None

    with open(pathtofile, 'rb') as demo_file:
        if readStr(demo_file, 8) == 'HL2DEMO':
            infos = DemoInfo()
            infos.dem_prot = readInt(demo_file)
            infos.net_prot = readInt(demo_file)
            infos.host_name = readStr(demo_file)
            infos.client_name = readStr(demo_file)
            infos.map_name = readStr(demo_file)
            infos.gamedir = readStr(demo_file)
            infos.time = readFloat(demo_file)
            infos.ticks = readInt(demo_file)
            infos.frames = readInt(demo_file)
            infos.tickrate = int(infos.ticks / infos.time)
            if(IsGoodIPPORTFormat(infos.host_name)):
                infos.demo_type = 0     # RIE   TODO : Add localhost:PORT check.
            else:
                infos.demo_type = 1     # TV
            infos.status_present = False
            if not fast and infos.demo_type != 1:   # No status in TV records.
                l = demo_file.readline()
                while(l != ''):
                    if "\x00status\x00" not in l:
                        infos.status_present = True
                        break
            else:
                l = demo_file.readline()
                print(l)
        else:
            print("Bad file format.")
    return infos

def main():
    pathtofile = input('path to demo>')
    print('parsing {}'.format(pathtofile))
    demo_info = getDemoInfo(pathtofile)
    print('Demo protocol version: {}'.format(demo_info.dem_prot))
    print('Network protocol version: {}'.format(demo_info.net_prot))
    print('HOSTNAME in case of TV, and IP:PORT or localhost:PORT in case of RIE (Record In eyes): {}'.format(demo_info.host_name))
    print('Client name or TV name: {}'.format(demo_info.client_name))
    print('Map name: {}'.format(demo_info.map_name))
    print('Root game directory: {}'.format(demo_info.gamedir))
    print('Playback time (s): {}'.format(demo_info.time))
    print('Number of ticks: {}'.format(demo_info.ticks))
    print('Number of frames: {}'.format(demo_info.frames))
    print('Tickrate: {}'.format(demo_info.tickrate))


if __name__ == '__main__':
    main()
