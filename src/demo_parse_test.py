import struct
import socket
import io
import enum

import cstrike15_gcmessages_pb2
import netmessages_public_pb2

DEMO_BUFFER_SIZE = 2 * 1024 * 1024

# default settings, no output
# TODO: make naming consistent and make all false by default
DUMP_GAME_EVENTS = False
SUPRESS_FOOTSTEP_EVENTS = True
SHOW_EXTRA_PLAYER_INFO_IN_GAME_EVENTS = False
DUMP_DEATHS = False
SUPRESS_WARMUP_DEATHS = True
DUMP_STRING_TABLES = False
DUMP_DATA_TABLES = False
DUMP_PACKET_ENTITIES = False
DUMP_NET_MESSAGES = False

# this should possibly be in a different file
# not sure about how the Int and Int64 differences translate from c++
SEND_PROP_TYPE = enum('DPT_Int', 
                      'DPT_Float',
                      'DPT_Vector',
                      'DPT_VectorXY',   # vector that ignores the z coordinate
                      'DPT_String',
                      'DPT_Array',
                      'DPT_DataTable',
                      'DPT_Int64',
                      'DPT_NUMSendPropTypes')

# constants defined in demofilepropdecode.h, only taking what is needed
SPROP_EXCLUDE     = 1 << 6  # ?? points at another prop to be excluded
SPROP_INSIDEARRAY = 1 << 8  # property is inside array, shouldn't be flattened

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

def read_varint32(bytes_in):
    '''takes a bytes that conatains a varint32 and returns it as a normal int'''
    val = 0
    shift = 0

    while True:
        byte = bytes_in.read(1)
        if byte == b'':
            raise EOFError()

        val |= (byte[0] &  0x7f) << shift
        shift += 7

        if not (byte[0] & 0x80):
            break

    return val

def read_cmd_header(demo_file):
    '''reads a cmd, tick, and player_slot'''
    cmd = read_byte(demo_file)

    if cmd <= 0:
        raise EOFError('Missing end tag in demo file')

    tick = read_int(demo_file)

    player_slot = read_byte(demo_file)

    return cmd, tick, player_slot


def read_raw_data(demo_file, length):
    '''read a something (frame?) of bytes from the file'''
    size = read_int(demo_file)

    buf = demo_file.read(size)

    return buf

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

def read_from_buffer(data_bytes):
    '''takes a bytesio file and reads a different something'''
    table_size = read_varint32(data_bytes)
    data_read = read_raw_data(data_bytes, table_size)
    return data_read

def recv_table_read_infos(msg):
    '''extracts data from the msg object, which is a CSVCMsg_SendTable()'''
    if DUMP_DATA_TABLES:
        print('{}:{}'.format(msg.net_table_name(), msg.props_size()))
        for iProp in range(msg.props_size()):
            send_prop = msg.props(iProp)
            
            exclude = send_prop.flags() & SPROP_EXCLUDE
            flags_in_array = send_prop.flags() & SPROP_INSIDEARRAY
            in_array_str = ' inside array' if flags_in_array else ''

            # this uses send_prop.type() in c++
            if send_prop.type() == SEND_PROP_TYPE.DPT_DataTable or
               exclude:
                print('{}:{:6}:{}:{}{}'.format(send_prop.type(), 
                                               send_prop.flags(),
                                               send_prop.var_name(),
                                               send_prop.dt_name(),
                                               ' exclude' if exclude else ''))
            elif send_prop.type() == SEND_PROP_TYPE.DPT_Array:
                print('{}:{:6}:{}[{}]'.format(send_prop.type(),
                                              send_prop.flags(),
                                              send_prop.var_name(),
                                              send_prop.num_elements()))
            else:
                print('{}:{:6}:{}:{},{},{:8},{}'.format(send_prop.type(),
                                                        send_prop.flags(),
                                                        send_prop.var_name(),
                                                        send_prop.low_value(),
                                                        send_prop.high_value(),
                                                        send_prop.num_bits(),
                                                        in_array_str))

def parse_data_table(data_table_bytes):
    '''reads and parses a data table'''
    msg = netmessages_public_pb2.CSVCMsg_SendTable()
    while True:
        data_type = read_varint32(data_table_bytes) # intentionally ignored
        data_read = read_from_buffer(data_table_bytes)  #this may silently fail
        
        msg.ParseFromString(data_read)  # probably wrong, but is my best guess
        # this is ParseFromArray in demofiledump.cpp but that doesn't seem to
        # exist.

        if msg.is_end():
            # not really sure how this is defined or how it works
            break



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
            buf = read_raw_data(demo_file, 0)
        elif tick == 6:
            '''datatables, somewhat confusing'''
            data_table_bytes = io.BytesIO(read_raw_data(demo_file, DEMO_BUFFER_SIZE))
            parse_data_table(data_table_bytes)


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
