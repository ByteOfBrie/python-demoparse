import struct
import socket
import io

DEMO_BUFFER_SIZE = 2 * 1024 * 1024

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

def read_str(demo_file, n=260):
    return demo_file.read(n).decode('utf-8').strip('\x00')

def read_int(demo_file, n=4):
    val = struct.unpack('=i', demo_file.read(n))[0]
    return val

def read_float(demo_file, n=4):
    return struct.unpack('=f', demo_file.read(n))[0]

def read_byte(demo_file):
    '''read unsigned char from the file'''
    return struct.unback('=B', demo_file.read(1))[0]
 
def IsGoodIPPORTFormat(ip_str):
    '''check for valid ip adress, does not need to be perfect'''
    ip_str = ip_str.replace('localhost', '127.0.0.1')
    try:
        socket.inet_aton(ip_str)
        return True
    except socket.error:
        return False
 
def get_demo_info(pathtofile = None, demo_file = None):
    '''reads the header of a demo_file, openening if necessary''' 
    infos = None
    
    if read_str(demo_file, 8) == 'HL2DEMO':
        infos = DemoInfo()
        infos.dem_prot = read_int(demo_file)
        infos.net_prot = read_int(demo_file)
        infos.host_name = read_str(demo_file)
        infos.client_name = read_str(demo_file)
        infos.map_name = read_str(demo_file)
        infos.gamedir = read_str(demo_file)
        infos.time = read_float(demo_file)
        infos.ticks = read_int(demo_file)
        infos.frames = read_int(demo_file)
        infos.tickrate = int(infos.ticks / infos.time)
        if(IsGoodIPPORTFormat(infos.host_name)):
            infos.demo_type = 0     # RIE   TODO : Add localhost:PORT check.
        else:
            infos.demo_type = 1     # TV
    else:
        print("Bad file format.")
    return infos

def read_cmd_header(demo_file):
    '''reads a cmd, tick, and player_slot'''
    cmd = read_byte(demo_file)

    if cmd <= 0:
        raise EOFError('Missing end tag in demo file')

    tick = read_int(demo_file)

    player_slot = read_byte(demo_file)

    return cmd, tick, player_slot


def read_raw_data(demo_file, length):
    size = read_int(demo_file)

    buff = demo_file.read(size)

    return buff, size

class bitbuf():
    '''parses or something'''
    def __init__(self, data, buffer_size=DEMO_BUFFER_SIZE):
        self.mask_table = [0, ( 1 << 1 ) - 1, ( 1 << 2 ) - 1, ( 1 << 3 ) - 1,
                          ( 1 << 4 ) - 1, ( 1 << 5 ) - 1, ( 1 << 6 ) - 1, 
                          ( 1 << 7 ) - 1, ( 1 << 8 ) - 1, ( 1 << 9 ) - 1, 
                          ( 1 << 10 ) - 1, ( 1 << 11 ) - 1, ( 1 << 12 ) - 1,
                          ( 1 << 13 ) - 1, ( 1 << 14 ) - 1, ( 1 << 15 ) - 1, 
                          ( 1 << 16 ) - 1, ( 1 << 17 ) - 1, ( 1 << 18 ) - 1,
                          ( 1 << 19 ) - 1, ( 1 << 20 ) - 1, ( 1 << 21 ) - 1,
                          ( 1 << 22 ) - 1, ( 1 << 23 ) - 1, ( 1 << 24 ) - 1,
                          ( 1 << 25 ) - 1, ( 1 << 26 ) - 1, ( 1 << 27 ) - 1,
                          ( 1 << 28 ) - 1, ( 1 << 29 ) - 1, ( 1 << 30 ) - 1,
                          0x7fffffff, 0xffffffff]
        self.data = data
        self.buffer_size = buffer_size  # maybe not needed

    def get_num_bits_read(self):
        '''number of bits read by this object, needs to be pythonified'''
        if self.data = None:
            return None

        n_cur_ofs = (self.data_in - self.data)/4 - 1

        n_cur_ofs *= 32
        n_cur_ofs += (32 - self.n_bits_avail)
        n_adjust = 8 * (self.n_data_bytes & 3)
        return min(n_cur_ofs + n_adjust, self.n_data_bytes)

    def get_num_bytes_read(self):
        '''get_num_bits_read, but returns bytes'''
        return (self.get_num_bytes_read() + 7) >> 3

    def get_num_byte_left(self):
        '''bytes left to be read'''
        pass

def parse_data_table(data):
    '''reads and parses a data table'''


def dump(demo_file):
    '''gets the information from the demo'''
    match_started = False
    demo_finished = False

    while not demo_finished:
        cmd, tick, player_slot = read_cmd_header(demo_file)

        current_tick = tick

        if tick == 3:
            '''synctick, doesn't seem to do anything'''
            pass
        elif tick == 7:
            '''stop tick'''
            demo_finished = True
        elif tick == 4:
            '''console command, nothing seems to be saved'''
            buff, size = read_raw_data(demo_file, 0)
        elif tick == 6:
            '''datatables, bitbuf library not finished'''
            data, size = read_raw_data(demo_file, DEMO_BUFFER_SIZE)
            #parse_data_table


def main():
    pathtofile = input('path to demo>')
    print('parsing {}'.format(pathtofile))
    demo_file = open(pathtofile, 'rb')
    demo_info = get_demo_info(demo_file)
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
