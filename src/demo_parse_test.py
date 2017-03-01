import socket
from collections import namedtuple

import cstrike15_usermessages_public_pb2
import netmessages_public_pb2

from bitstring import ConstBitStream

DEBUG = True

NET_MAX_PAYLOAD = 262144 - 4
DEMO_BUFFER_SIZE = 2 * 1024 * 1024

MAX_PLAYER_NAME_LENGTH = 128
MAX_CUSTOM_FILES = 4
SIGNED_GUID_LEN = 32

ENTITY_SENTINEL = 9999

MAX_STRING_TABLES = 64  # can probably be deleted at some point

MAX_SPLITSCREEN_CLIENTS = 2

SERVER_CLASS_BITS = 0
NUM_NETWORKED_EHANDLE_SERIAL_BITS = 10

SUBSTRING_BITS = 5
MAX_USERDATA_BITS = 14

FHDR_ZERO = 0
FHDR_LEAVEPVS = 1
FHDR_DELETE = 2
FHDR_ENTERPVS = 4

SERVER_CLASSES = []     # list of ServerClass
DATA_TABLES = []        # list of CSVCMsg_SendTable
CURRENT_EXCLUDES = []   # list of ExcludeEntry
ENTITIES = []           # list of EntityEntry
PLAYER_INFOS = []       # list of player_info

STRING_TABLES = []      # list of StringTable

# default settings, no output
# TODO: make naming consistent
DUMP_GAME_EVENTS = False
DUMP_FOOTSTEP_EVENTS = False
SHOW_EXTRA_PLAYER_INFO_IN_GAME_EVENTS = False
DUMP_DEATHS = False
DUMP_WARMUP_DEATHS = False
DUMP_STRING_TABLES = False
DUMP_DATA_TABLES = False
DUMP_PACKET_ENTITIES = False
DUMP_NET_MESSAGES = False

# these shouldn't be globals, but there isn't a demo object yet
GAME_EVENT_LIST = netmessages_public_pb2.CSVCMsg_GameEventList()
MATCH_START_OCCURED = False

# these two seem to be the same thing, but they're differentiated in C++
Vector = namedtuple('Vector', ['x', 'y', 'z'])
QAngle = namedtuple('QAngle', ['x', 'y', 'z'])

# this should possibly be in a different file
# not sure about how the Int and Int64 differences translate from c++
class SEND_PROP_TYPE:
    DPT_Int = 0
    DPT_Float = 1
    DPT_Vector = 2
    DPT_VectorXY = 3  # vector that ignores the z coordinate
    DPT_String = 4
    DPT_Array = 5
    DPT_DataTable = 6
    DPT_Int64 = 7
    DPT_NUMSendPropTypes = 8

# constants defined in demofilepropdecode.h
SPROP_UNISGNED      = 1 << 0    # ?? unsigned integer data
SPROP_COORD         = 1 << 1    # ?? float/vector is treated like a world coord
SPROP_NOSCALE       = 1 << 2    # floating point doesn't scale, just takes value
SPROP_EXCLUDE       = 1 << 6    # ?? points at another prop to be excluded
SPROP_INSIDEARRAY   = 1 << 8    # property is inside array, shouldn't flatten
SPROP_COLLAPSIBLE   = 1 << 11   # in C++ is set if it's a database with an
                                # offset of 0 that doesn't change the pointer
                                # not sure what this does in python

# TODO: rename class and methods to be more pythonic
# TODO: evaluate moving to another file
class ServerClass():
    """data storage of something"""
    def __init__(self):
        """set the default values, allocate space for array"""
        nClassID = None
        strName = None 
        strDTName = None
        nDataTable = None

        flattened_props = [] # list of FlattenedPropEntry

class ExcludeEntry():
    """data storage for exclude entry"""
    def __init__(self, var_name, DTName, DTExcluding):
        """sets initial values"""
        self.var_name = var_name
        self.DTName = DTName
        self.DTExcluding = DTExcluding

class FlattenedPropEntry():
    """data storage for flattened properties"""
    def __init__(self, prop, array_element_prop):
        """sets initial values"""
        self.prop = prop
        self.array_element_prop = array_element_prop

class DemoInfo():
    """data storage for basic info about the demo contained in the header"""
    def __init__(self):
        """create default values and what they mean"""
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

class PlayerInfo():
    """storage class for data about player"""
    def __init__(self, data=None):
        """try to parse from raw data, probably won't work"""
        if data is None:
            self.version = None
            self.xuid = None
            self.name = None
            self.userID = None
            self.guid = None
            self.friendsID = None
            self.friendsName = None
            self.fakeplayer = None
            self.ishltv = None
            self.custom_files = None
            self. files_downloaded = None
            self.entityID = None
        else:
            self.version = read_uint64(data)
            self.xuid = read_uint64be(data)
            self.name = read_str(data, n = MAX_PLAYER_NAME_LENGTH)
            self.userID = read_int(data)
            self.guid = read_str(data, n = SIGNED_GUID_LEN+1)
            pad_stream(data, n = 24)
            self.friendsID = read_uint32(data)
            self.friendsName = read_str(data, MAX_PLAYER_NAME_LENGTH)

            self.fakeplayer = read_bool(data)
            self.ishltv = read_bool(data)
            pad_stream(data, n = 16)
            self.custom_files = read_custom_files(data)
            self.files_downloaded = read_byte(data)
            pad_stream(data, n = 24)
            self.entityID = read_int(data)

class split_t():
    """data storage and parsing for a view angle"""
    def __init__(self, data_bytes):
        """parses bytes to view angles"""
        self.flags = read_int(data_bytes)

        # original origin/view angles
        self.viewOrigin = Vector(read_float(data_bytes),
                                 read_float(data_bytes),
                                 read_float(data_bytes))
        self.viewAngles = QAngle(read_float(data_bytes),
                                 read_float(data_bytes),
                                 read_float(data_bytes))
        self.localViewAngles = QAngle(read_float(data_bytes),
                                      read_float(data_bytes),
                                      read_float(data_bytes))

        # resampled origin/view angles
        self.viewOrigin2 = Vector(read_float(data_bytes),
                                  read_float(data_bytes),
                                  read_float(data_bytes))
        self.viewAngles2 = QAngle(read_float(data_bytes),
                                  read_float(data_bytes),
                                  read_float(data_bytes))
        self.localViewAngles2 = QAngle(read_float(data_bytes),
                                       read_float(data_bytes),
                                       read_float(data_bytes))


class demo_cmd_info():
    """data storage and parsing for a demo_cmd"""
    def __init__(self, data_bytes):
        """takes in bytes and creates the demo_cmd_info class"""
        self.u = []
        self.u.add(split_t(read_bytes, 76))
        self.u.add(split_t(read_bytes, 76))

def read_str(demo_stream, n=260):
    """reads a string of n bytes, decodes it as utf-8 and strips null bytes"""
    return demo_stream.read('bytes:{}'.format(n)).decode('utf-8').strip('\x00')

def read_int(demo_stream):
    """little endian signed int 32"""
    return demo_stream.read('intle:32')

def read_intbe(demo_stream):
    """big endian signed int 32"""
    return demo_stream.read('intbe:32')

def read_uint32(demo_stream):
    """little endian unsigned int 32"""
    return demo_stream.read('uintle:32')

def read_uint32be(demo_stream):
    """big endian unsigned int 32"""
    return demo_stream.read('uintbe:32')

def read_uint64(demo_stream):
    """little endian unsigned in 64"""
    return demo_stream.read('uintle:64')

def read_uint64be(demo_stream):
    """big endian unsigned int 64"""
    return demo_stream.read('uintbe:64')

def read_float(demo_stream):
    """little endian 32 bit float"""
    return demo_stream.read('floatle:32')

def read_bytes(demo_stream, n):
    """read n bytes from the stream"""
    return demo_stream.read('bytes:{}'.format(n))

def read_byte(demo_stream):
    """read unsigned char from the file"""
    return demo_stream.read('uintle:8')

def read_short(demo_stream):
    """read signed short from the file"""
    return demo_stream.read('intle:16')

def read_word(demo_stream):
    """read an unsigned short from the file"""
    return demo_stream.read('uintle:16')

def read_bit(demo_stream):
    """read a single bit and return it as a bool"""
    return demo_stream.read('bool')

def read_uchar(demo_stream):
    """read an 1 byte unsigned char"""
    return demo_stream.read('uintle:8')

def read_bool(demo_stream):
    """reads a entire byte and evaluates it as a bool"""
    return bool(demo_stream.read(8))

def read_ulong(demo_stream):
    """read unsigned long 32 bits"""
    return demo_stream.read('uintle:32')

def read_custom_files(demo_stream):
    """read 4 unsigned longs into a list"""
    return [read_ulong(demo_stream), read_ulong(demo_stream),
            read_ulong(demo_stream), read_ulong(demo_stream)]

def pad_stream(demo_stream, n):
    """ignore n bits. this function only exists to make bitstring easier
    to replace with another library in the future
    """
    demo_stream.read('pad:{}'.format(n))

def read_raw_data(demo_stream):
    """read a something (frame?) of bytes from the file"""
    size = read_int(demo_stream)

    return demo_stream.read(size)

def read_user_cmd(demo_stream):
    """I don't think this is actually used to collect data"""
    outgoing = read_int(demo_stream)

    read_raw_data(demo_stream)

    return outgoing

def IsGoodIPPORTFormat(ip_str):
    """check for valid ip adress, does not need to be perfect"""
    ip_str = ip_str.replace('localhost', '127.0.0.1')
    try:
        socket.inet_aton(ip_str)
        return True
    except socket.error:
        return False

def get_demo_info(demo_stream):
    """reads the header of a binary stream of a demo file"""
    infos = None

    if demo_stream is None:
        raise ValueError('demo_file is None')

    if read_str(demo_stream, 8) == 'HL2DEMO':
        infos = DemoInfo()
        infos.dem_prot = read_int(demo_stream)
        infos.net_prot = read_int(demo_stream)
        infos.host_name = read_str(demo_stream)
        infos.client_name = read_str(demo_stream)
        infos.map_name = read_str(demo_stream)
        infos.gamedir = read_str(demo_stream)
        infos.time = read_float(demo_stream)
        infos.ticks = read_int(demo_stream)
        infos.frames = read_int(demo_stream)
        infos.tickrate = int(infos.ticks / infos.time)
        if(IsGoodIPPORTFormat(infos.host_name)):
            infos.demo_type = 0     # RIE
        else:
            infos.demo_type = 1     # TV
    else:
        print('Bad file format.')
    return infos

def read_varint32(data_stream):
    """takes a bytes that conatains a varint32 and returns it as a normal int"""
    val = 0
    shift = 0

    while True:
        byte = read_byte(data_stream)
        if byte == b'':
            raise EOFError()

        val |= (byte[0] &  0x7f) << shift
        shift += 7

        if not (byte[0] & 0x80):
            break

    return val

def read_cmd_header(demo_file):
    """reads a cmd, tick, and player_slot"""
    cmd = read_byte(demo_file)

    if cmd <= 0:
        raise EOFError('Missing end tag in demo file')

    tick = read_int(demo_file)

    player_slot = read_byte(demo_file)

    return cmd, tick, player_slot

def read_cmd_info(data_stream):
    demo_cmd_bytes = read_bytes(data_stream, 156)
    demo_cmd_info(demo_cmd_bytes)

def read_from_buffer(data_bytes):
    """takes a bytesio file and reads a different something"""
    table_size = read_varint32(data_bytes)
    data_read = read_raw_data(data_stream)
    return data_read

def recv_table_read_infos(msg):
    """extracts data from the msg object, which is a CSVCMsg_SendTable()"""
    if DUMP_DATA_TABLES:
        print('{}:{}'.format(msg.net_table_name(), msg.props_size()))
        for iProp in range(msg.props_size()):
            send_prop = msg.props(iProp)
            
            exclude = send_prop.flags() & SPROP_EXCLUDE
            flags_in_array = send_prop.flags() & SPROP_INSIDEARRAY
            in_array_str = ' inside array' if flags_in_array else ''

            # this uses send_prop.type() in c++
            if send_prop.type() == SEND_PROP_TYPE.DPT_DataTable or exclude:
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

def get_table_by_name(name):
    """finds a table given a string name"""
    for i in range(len(DATA_TABLES)):
        if DATA_TABLES[i].net_table_name() == name:
            return DATA_TABLES[i]
    return None

def is_prop_included(pTable, send_prop):
    """determines if prop is included??"""
    for i in range(len(CURRENT_EXCLUDES)):
        if (pTable.net_table_name() == CURRENT_EXCLUDES[i].DTName and
            send_prop.var_name() == CURRENT_EXCLUDES[i].var_name):
            return True
    return False

def gather_excludes(data_table):
    """
    finds excludes for the particular data table
    not sure why this needs to be called seperately for each table
    """
    for i in range(data_table.props_size()):
        send_prop = data_table[i]   # may not work
        
        if send_prop.flags() & SPROP_EXCLUDE:
            CURRENT_EXCLUDES.add(ExcludeEntry(send_prop.var_name(),
                                              send_prop.dt_name(),
                                              data_table.net_table_name()))
        
        if send_prop.type() == SEND_PROP_TYPE.DPT_DataTable:
            sub_table = get_table_by_name(send_prop.dt_name())
            if sub_table is not None:
                gather_excludes(sub_table)

def gather_props_iterate_props(pTable, server_class, flattened_props):
    """iterates over something, part of gather_props"""
    for i in range(pTable.props_size()):
        send_prop = pTable[i]   # C++: pTable->props( iProp )
        if (send_prop.flags() & SPROP_INSIDEARRAY or
                send_prop.flags() & SPROP_EXCLUDE or
                is_prop_excluded(pTable, send_prop)):
            continue
        if send_prop.type() == SEND_PROP_TYPE.DPT_DataTable:
            sub_table = get_table_by_name(send_prop.dt_name())

            if sub_table is not None:
                if send_prop.flags() & SPROP_COLLAPSIBLE:
                    gather_props_iterate_props(sub_table, server_class, 
                                               flattened_props)
                else:
                    gather_props(sub_table, server_class)
        else:
            if send_prop.type() == SEND_PROP_TYPE.DPT_Array:
                flattened_props.add(FlattenedPropEntry(send_prop, pTable[i-1]))
            else:
                flattened_props.add(FlattenedPropEntry(send_prop, None))

def gather_props(pTable, server_class):
    """gathers properties?"""
    temp_flattened_props = []   # list of FlattenedPropEntry
    gather_props_iterate_props(pTable, server_class, temp_flattened_props)

    flattened_props = SERVER_CLASSES[server_class].flattened_props

    for flattened_prop in temp_flattened_props:
        flattened_props.add(flattened_prop)

    #not sure what happens to flattened_props here

def flatten_data_table(server_class):
    """flattens a data table?"""
    table = DATA_TABLES[SERVER_CLASSES[server_class].nDataTable]
    table.clear()      # TODO: make more pythonic
    gather_excludes(table)

    gather_props(table, server_class)

    priorities.add(64)
    

    for flattened_prop in flattened_props:
        priority = flattened_prop.priority()

        if priority not in priorities:
            priorities.add(priority)

    priorities.sort()

    # sort flattened_props by property
    start = 0
    for priority in priorities:
        while True:
            current_prop = start
            while current_prop < len(flattened_props):
                prop = flattened_props[current_prop].prop   # maybe not .prop?
                if (prop.priority() == priority or (priority == 64 and
                    (SPROP_CHANGES_OFTEN & prop.flags()))):
                    if start != current_prop:
                        flattened_props[start], flattened_props[current_prop] = flattened_props[current_prop], flattened_props[start]
                    start += 1
                    break
                current_prop += 1
            if current_prop == len(flattened_props):
                break

def parse_data_table(data_table_bytes):
    """reads and parses a data table"""
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

        recv_table_read_infos(msg)

        DATA_TABLES.add(msg)

    server_classes = read_short(data_table_bytes)

    # c++ contains assert here, ignoring for now

    for i in range(server_classes):
        entry = ServerClass()
        entry.nClassID = read_short(demo_file)

        if (entry.nClassID >= server_classes):
            raise IndexError('invalid class index {}'.format(entry.nClassID))
        read_str(entry.strName, len(entry.strName))
        read_str(entry.strDTName, len(entry.strDTName))

        # ?? find the data table by name
        entry.nDataTable = -1
        for j in range(len(DATA_TABLES)):
            if entry.strDTName == DATA_TABLES[j].net_table_name():
                entry.nDataTable = j
                break

        if DUMP_DATA_TABLES:
            print('class:{}:{}:{}({})'.format(entry.nClassID,
                                              entry.strName,
                                              entry.strDTName,
                                              entry.nDataTable))
    if DUMP_DATA_TABLES:
        print('Flattening data tables...')

    for i in range(server_classes):
        flatten_data_table(i)

    if DUMP_DATA_TABLES:    # not sure what the point of this is
        print('Done')

    temp = server_classes
    SERVER_CLASS_BITS = 0
    temp >>= 1
    while temp:
        temp >>= 1
        SERVER_CLASS_BITS += 1
    SERVER_CLASS_BITS += 1
    return msg

def find_player_by_entity(entityID):
    """search through PLAYER_INFOS for an ID of entityID"""
    for index, entity in enumerate(PLAYER_INFOS):
        if entity.entityID == entityID:
            return index
    return None

def dump_string_table(data_table_bytes, is_user_info):
    """parses an individual string table"""
    numstrings = read_word(data_table_bytes)

    if DUMP_STRING_TABLES:
        print(numstrings)

    if is_user_info:
        if DUMP_STRING_TABLES:
            print('Clearing player info array.')
        PLAYER_INFOS.clear()

    for i in range(numstrings):
        stringname = read_str(data_table_bytes, n=4096)
        assert(len(stringname) < 100)       # probably shouldn't be here

        if read_bit(data_table_bytes):
            user_data_size = read_word(data_table_bytes)
            assert(user_data_size > 0)
            data = read_bytes(user_data_size)

            if is_user_info and data is not None:
                player_info = PlayerInfo(data)
                player_info.entityID = i

                existing = find_player_by_entity(i)
                if existing is None:
                    if DUMP_STRING_TABLES:
                        print('adding player entity {} info:'.format(i))
                        print('xuid:{}'.format(player_info.xuid))
                        print('name:{}'.format(player_info.name))
                        print('userID:{}'.format(player_info.userID))
                        print('guid:{}'.format(player_info.guid))
                        print('friendsID:{}'.format(player_info.friendsID))
                        print('friendsName:{}'.format(player_info.fakeplayer))
                        print('ishltv:{}'.format(player_info.ishltv))
                        print('filesDownloaded:{}'.format(player_info.filesDownloaded))
                    PLAYER_INFOS.add(player_info)
                else:
                    # should never happen, but just in case
                    PLAYER_INFOS[existing] = player_info
            else:
                if DUMP_STRING_TABLES:
                    print(' {}, {}, userdata[{}]'.format(i, stringname,
                                                         user_data_size))
        else:
            if DUMP_STRING_TABLES:
                print(' {}, {}'.format(i, stringname))

    if read_bit(data_table_bytes):
        numstrings = read_word(data_table_bytes)
        for i in range(numstrings):
            stringname = read_str(data_table_bytes, n=4096)
            if read_bit(data_table_bytes):
                user_data_size = read_word(data_table_bytes)
                assert(user_data_size > 0)

                data = read_bytes(data_table_bytes, n=user_data_size)

                if i >= 2:
                    if DUMP_STRING_TABLES:
                        print(' {}, {}, userdata[{}]'.format(i, stringname,
                                                             user_data_size))
            else:
                if i >= 2:
                    if DUMP_STRING_TABLES:
                        print(' {}, {}'.format(i, stringname))


def dump_string_tables(data_table_bytes):
    """seperates out string tables and then passes them to dump_string_table"""
    num_tables = read_byte(data_table_bytes)

    for i in range(num_tables):
        tablename = read_str(data_table_bytes, n=256)

        if DUMP_STRING_TABLES:
            print('ReadStringTable:{}'.format(tablename))

        # might be issues coming from tablename being padded with null bytes
        is_user_info = tablename == 'userinfo'

        dump_string_table(data_table_bytes, is_user_info)

def read_sequence_info(data_stream):
    """takes bytes in and reads two ints"""
    sequence_num_in = read_int(data_stream)
    sequence_num_out = read_int(data_stream)
    return (sequence_num_in, sequence_num_out)

def demo_msg_print(msg, size):
    """prints out some debug info, designed to be similar to the c version"""
    print('--- {} ({} bytes) --------'.format(type(msg), size))
    print(msg)      # should be defined but may not actually work

def print_user_message(user_msg):
    """parses and then prints user message"""
    cmd = user_msg.msg_type
    size_um = len(user_msg.msg_data)
    types = [cstrike15_usermessages_public_pb2.CCSUsrMsg_VGUIMenu,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Geiger,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Train,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_HudText,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SayText,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SayText2,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_TextMsg,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_HudMsg,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ResetHud,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_GameTitle,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Shake,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Fade,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Rumble,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_CloseCaption,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_CloseCaptionDirect,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SendAudio,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_RawAudio,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_VoiceMask,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_RequestState,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_Damage,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_RadioText,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_HintText,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_KeyHintText,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ProcessSpottedEntityUpdate,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ReloadEffect,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_AdjustMoney,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_StopSpectatorMode,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_KillCam,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_DesiredTimescale,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_CurrentTimescale,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_AchievementEvent,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_MatchEndConditions,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_DisconnectToLobby,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_PlayerStatsUpdate,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_DisplayInventory,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_WarmupHasEnded,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ClientInfo,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_XRankGet,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_XRankUpd,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_CallVoteFailed,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_VoteStart,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_VotePass,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_VoteFailed,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_VoteSetup,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ServerRankRevealAll,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SendLastKillerDamageToClient,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ServerRankUpdate,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ItemPickup,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ShowMenu,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_BarTime,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_AmmoDenied,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_MarkAchievement,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_MatchStatsUpdate,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ItemDrop,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_GlowPropTurnOff,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SendPlayerItemDrops,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_RoundBackupFilenames,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_SendPlayerItemFound,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ReportHit,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_XpUpdate,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_QuestProgress,
             cstrike15_usermessages_public_pb2.CCSUsrMsg_ScoreLeaderboardData]
    msg = types[cmd]()
    msg.ParseFromString(user_msg.msg_data)
    demo_msg_print(msg, um_size)

def dump_user_message(data_stream, size):
    """deals with the user message type of packets"""
    user_msg = netmessages_public_pb2.CSVCMsg_UserMessage()
    user_msg.ParseFromString(read_bytes(data_stream, size))
    print_user_message(msg)

def handle_svc_user_message(data_stream, size, cmd):
    """handles a packet of type svc_user_message"""
    dump_user_messages(data_stream, size)

def get_game_event_descriptor(msg):
    """finds the descriptor in GAME_EVENT_LIST"""
    #TODO: add demo class or object and change this function
    found = False
    for i in range(len(GAME_EVENT_LIST.descriptors)):
        descriptor = GAME_EVENT_LIST.descriptors[i]
        if descriptor.eventid == msg.eventid:
            found = True
            break

    if not found:
        if DUMP_GAME_EVENTS:
            print(msg)
        return None
    return GAME_EVENT_LIST.descriptors[i]

def find_player_info(index):
    """given an index goes and gets information about a player"""
    for player in PLAYER_INFOS:
        if player.userID == index:
            return player

def show_player_info(field, index, show_details=True, bCSV=False):
    """prints some stuff about a player"""
    player_info = find_player_info(index)
    if player_info is None:
        return False
    if bCSV:
        print('{}, {}, {}'.format(field, player_info.name, index), end='')
    else:
        print(' {}: {} (id:{})'.format(field, player_info, index))
    
    if show_details:
        entity_index = player_info.entityID + 1
        entity = find_entity(entity_index)
        assert(entity is not None)
        XYProp = entity.FindProp("m_vecOrigin")
        ZProp = entity.FindProp("m_vecOrigin[2]")
        if (XYProp is not None and ZProp is not None):
            if bCSV:
                print(', {}, {}, {}'.format(XYProp.m_pPropValue.m_value.m_vector.x,
                                            XYProp.m_pPropValue.m_value.m_vector.y,
                                            XYProp.m_pPropValue.m_value.m_vector.z),
                      end='')
            else:
                print(' position: {}, {}, {}'.format(XYProp.m_pPropValue.m_value.m_vector.x,
                                                     XYProp.m_pPropValue.m_value.m_vector.y,
                                                     XYProp.m_pPropValue.m_value.m_vector.z))
        angle0Prop = entity.FindProp('m_angEyeAngles[0]')
        angle1Prop = entity.FindProp('m_angEyeAngles[1]')
        if angle0Prop is not None and angle1Prop is not None:
            if bCSV:
                print(', {}, {}'.format(angle0Prop.m_pPropValue.m_value.m_float,
                                        angle1Prop.m_pPropValue.m_value.m_float),
                                        end = '')
            else:
                print(' facing: pitch:{}, yaw:{}'.format(angle0Prop.m_pPropValue.m_value.m_float,
                                                         angle1Prop.m_pPropValue.m_value.m_float))
        team_prop = entity.FindProp('m_iTeamNum')
        if team_prop is not None:
            if bCSV:
                print(', {}'.format('T' if team_prop.m_pPropValue.m_value.m_int == 2 else 'CT'),
                      end='')
            else:
                print(' team: {}'.format('T' if team_prop.m_pPropValue.m_value.m_int == 2 else 'CT'))
    return True

def handle_player_death(msg, descriptor):
    """finds info about player death event"""
    userid = -1
    attackerid = -1
    assisterid = 0
    weapon_name = None
    headshot = False
    for i in range(len(msg.keys)):
        key = descriptor.keys[i]
        key_value = msg.keys[i]

        if key.name == 'userid':
            userid = key_value.data
        elif key.name == 'attacker':
            attackerid = key_value.data
        elif key.name == 'assister':
            assisterid = key_value.data
        elif key.name == 'weapon':
            weapon_name = key_value.data
        elif key.name == 'headshot':
            headshot = key_value.data
    
    show_player_info('victim', userid, True, True)
    print(', ', end='')
    show_player_info('attacker', attackerid, True, True)
    print(', {}, {}'.format(weapon_name, str(headshot), end=''))
    if assisterid != 0:
        print(', ', end='')
        show_player_info('assister', assisterid, True, True)
    print()

def handle_player_connect_events(msg, descriptor):
    """deals with sorting out when players both connect and disconnect"""
    player_disconnect = (descriptor.name == 'player_disconnect')
    if not player_disconnect:
        if descriptor.name != 'player_connect':
            return False
    userid = -1
    index = -1
    name = None
    bot = False
    reason = None
    
    for i in range(len(msg.keys)):
        key = descriptor.keys[i]
        key_value = msg.keys[i]

        if key.name == 'userid':
            userid = key.value
        elif key.name == 'index':
            index = key.value
        elif key.name == 'name':
            name = key.value
        elif key.name == 'networkid':
            print(key.value)        # this is to help with debugging
            bot = bool(key.value == 'BOT')
        elif key.name == 'bot':
            bot = key.value
        elif key.name == 'reason':
            reason = key.value

    if player_disconnect:
        if DUMP_GAME_EVENTS:
            print('Player {} (id:{}) has disconnected. Reason: {}'.format(name, userid, reason))
        player_info = find_player_info(userid)
        if player_info is not None:     # mark player spot as epmty
            player_info.name = 'disconnected'
            player_info.userid = -1
            player_info.guid[0] = 0
    else:
        new_player = PlayerInfo()
        new_player.userID = userid
        new_player.name = name
        new_player.fakeplayer = bot
        if bot:
            new_player.guid = 'bot'

        new_player.entityID = index
        
        existing = find_player_by_entity(index)

        if existing is None:
            if DUMP_GAME_EVENTS:
                print('Player {} {} (id:{}) connected.'.format(new_player.guid, name, userid))
            PLAYER_INFOS.append(new_player)
        else:
            existing = new_player
            # this doesn't actually work because it's not a pointer
            # but I'm putting it here because I want to
            # TODO: make a function to give the index of the existing player
            # so that it can assign to the position in the array
            # This could also be solved by giving a method to overwrite
            # exiting but that seems uglier
    return True

def parse_game_event(msg, descriptor):
    """gets the info from the game event"""
    if descriptor is None:
        raise ValueError('descriptor is None')
    if descriptor.name != 'player_footstep' or DUMP_FOOTSTEP_EVENTS:
        if not handle_player_connect_events(msg, descriptor):
            if descriptor.name == 'round_announce_match_start':
                MATCH_START_OCCURED = True
            allow_death_report = (MATCH_START_OCCURED or DUMP_WARMUP_DEATHS) and DUMP_DEATHS
            if descriptor.name == 'player_death' and allow_death_report:
                handle_player_death(msg, descriptor)
            if DUMP_GAME_EVENTS:
                print('{}\n{'.format(descriptor.name))
                for i in range(len(msg.keys)):
                    key = descriptor.keys[i]
                    key_value = msg.keys[i]
                    handled = False
                    if key.name == 'userid' or key.name == 'attacker' or key.name == 'assister':
                        # key_value.data is probably wrong, but I'm not sure what
                        # the correct way is to get the data
                        handled = show_player_info(key.name, key_value.data)
                    if not handled:
                        print(' {}:{}'.format(key.name, key))
                print('}')

def handle_svc_game_event(data_stream, size, cmd):
    """handles a packet of type svc_game_event"""
    msg = netmessages_public_pb2.CSVCMsg_GameEvent()
    msg.ParseFromString(data_stream.read('bytes:{}'.format(size)))
    descriptor = get_game_event_descriptor(data_stream, cmd)
    parse_game_event(msg, descriptor)

def parse_string_table_update(data_stream, entries, max_entries,
                              user_data_size, user_data_size_bits,
                              user_data_fixed_size, is_user_info):
    """parses a string table"""
    string_history_entry = None

    last_entry = -1
    last_dictionary_index = -1

    temp = max_entries
    temp >>= 1
    entry_bits = 0

    while temp:
        temp >>= 1
        entry_bits += 1

    encode_using_dictionaries = bool(read_bit(data_stream))
    if encode_using_dictionaries:
        raise ValueError('Cannot parse string table update when encoded with dictionaries')

    history = []

    for i in range(entries):
        entry_index = last_entry + 1
        
        if not bool(read_bit(data_stream)):
            entry_index = read_ubitlong(entry_bits)

        last_entry = entry_index

        if entry_index < 0 or entry_index >= max_entries:
            raise ValueError('bad string index {}'.format(entry_index))
        
        # this section is probably wrong and needs to be changed around
        pEntry = None
        entry = None
        substr = None

        if read_bit(data_stream):
            substring_check = bool(read_bit)
            if substring_check:
                index = read_ubit_long(data_stream, 5)
                bytes_to_copy = read_ubit_long(data_stream, SUBSTRING_BITS)
                entry = history[index].string
                substring = read_str(data_stream, 1024)
                entry = entry + substring
            else:
                entry = read_str(data_stream, 1024)
            pEntry = entry

        tempbuf = None
        user_data = None
        num_bytes = None

        if read_bit(data_stream):
            if user_data_fixed_size:
                # don't need to read length because it's fixed and
                # "was networked down already" ???
                num_bytes = user_data_size
                assert(num_bytes > 0)
                tempbuf = read_bits(data_stream, user_data_size_bits)
            else:
                num_bytes = read_ubit_long(data_stream, MAX_USERDATA_BITS)
                tempbuf = read_bytes(data_stream, num_bytes)
            user_data = tempbuf

        if pEntry is None:
            pEntry = ''

        if is_user_info and user_data is not None:
            unswapped_player_info = user_data   # probably need to do a conversion
        

def handle_svc_create_string_table(data_stream, size, cmd):
    """handles a packet of type svc_create_string_table"""
    msg = netmessages_public_pb2.CSVCMsg_CreateStringTable()
    msg.ParseFromString(read_bytes(data_steam, size))
    is_user_info = msg.name != "userinfo"
    if DUMP_STRING_TABLES:
        print('CreateStringTable:{}:{}:{}:{}:{}'.format(msg.name,
                                                        msg.max_entries,
                                                        msg.num_entries,
                                                        msg.user_data_size,
                                                        msg.user_data_size_bits))
    # here the c code makes data which is a `CBitRead` for the entirity of
    # string_data, this might need to be parsed by me later, but that can
    # be figured out at some point
    # TODO: implement parse_string_table_update
    parse_string_table_update(data_stream, msg.string_data,
                              msg.num_entries, msg.max_entries,
                              msg.user_data_size, msg.user_data_size_bit,
                              msg.user_data_fixed_size, is_user_info)
    new_string_table = StringTableData(szName = msg.name, max_entires = msg.max_entries)
    STRING_TABLES.append(new_string_table)
    
def handle_svc_update_string_table(data_stream, size, cmd):
    """handles a packet of type svc_update_string_table"""
    msg = netmessages_public_pb2.CSVCMsg_UpdateStringTable()
    msg.ParseFromString(read_bytes(data_steam, size))
    is_user_info = msg.name != "userinfo"
    if DUMP_STRING_TABLES:
        print('UpdateStringTable:{}({}):{}'.format(msg.table_id,
                                                   STRING_TABLES[msg.table_id].szName,
                                                   msg.num_changed_entries))
    # here the c code makes data which is a `CBitRead` for the entirity of
    # string_data, this might need to be parsed by me later, but that can
    # be figured out at some point
    # TODO: implement parse_string_table_update
    parse_string_table_update(data_stream, msg.string_data,
                              msg.num_changed_entries,
                              STRING_TABLES[msg.table_id].nMaxEntries,
                              0, 0, 0, is_user_info)
    # the c code prints out some stuff if it's a bad table here, but
    # instead we will just silently fail
    
def handle_svc_send_table(data_stream, size, cmd):
    """handles a packet of type svc_send_table"""
    msg = netmessages_public_pb2.CSVCMsg_SendTable()
    msg.ParseFromString(read_bytes(data_stream, size))
    recv_table_read_infos(msg)

def handle_svc_packet_entities(data_stream, size, cmd):
    """handles a packet of type svc_packet_entities"""
    msg = netmessages_public_pb2.CSVCMsg_PacketEntities()
    msg.ParseFromString(read_bytes(data_stream, size))
    # here the c code makes `entityBitBuffer` which is a `CBitRead` that
    # contains `msg.entity_data`, this might need to be parsed but I'm
    # willing to pretend that it doesn't need to be
    entity_bit_buffer = ConstBitStream(msg.entity_data)
    as_delta = msg.is_delta         # why is this a variable
    header_count = msg.updated_entries
    baseline = msg.baseline
    update_baseline = msg.update_baseline
    header_base = -1
    new_entity = -1
    update_flags = 0

    update_type = 3         # this is an enum type in c

    while update_type < 4:
        header_count -= 1
        is_entity = header_count >= 0

        if is_entity:
            update_flags = FHDR_ZERO        # zero, not sure why it's in a constant

            # TODO: implement read_ubitvar
            new_entity = header_base + 1 + read_ubitvar(entity_bit_buffer)
            header_base = new_entity

            # leave pvs flag
            if not read_bit(entity_bit_buffer):
                # enter pvs flag
                if read_bit(entity_bit_buffer):
                    update_flags = update_flags | FHDR_ENTERPVS
            else:
                update_flags = update_flags | FHDR_LEAVEPVS
                
                # ? force delete flag
                if read_bit(entity_bit_buffer):
                    update_flags = update_flags | FHDR_DELETE
        update_type = 3
        while update_type == 3:
            if not is_entity or new_entity >= ENTITY_SENTINEL:
                update_type = 4     # finished
            else:
                if update_flags & FHDR_ENTERPVS:
                    update_type = 0     # enter pvs
                elif update_flags & FHDR_LEAVEPVS:
                    update_type = 1     # leave pvs
                else:
                    update_type = 2     # delta pvs

            if update_type == 0:    # enter pvs
                u_class = read_ubitlong(entity_bit_buffer, SERVER_CLASS_BITS)
                u_serial_num = read_ubitlong(entity_bit_buffer, NUM_NETWORKED_EHANDLE_SERIAL_BITS)
                if DUMP_PACKET_ENTITIES:
                    print('Entity enters PVS: id:{}, class:{}, serial:{}'.format(new_entity,
                                                                                 u_class,
                                                                                 u_serial_num))
                #TODO: implement AddEntity
                entity = AddEntity(new_entity, u_class, u_serial_num)
                #TODO: implement read_new_entity
                read_new_entity(entity_bit_buffer, entity)
            elif update_type == 1:   # leave pvs
                if not as_delta:
                    raise ValueError('leave pvs on full update')
                if DUMP_PACKET_ENTITIES:
                    if update_flags & FHDR_DELETE:
                        print('entity leaves pvs and is deleted: id:{}'.format(new_entity))
                    else:
                        print('entity leaves pvs: id:{}'.format(new_entity))
                remove_entity(new_entity)   #TODO: implement remove_entity
            elif update_type == 2:  # delta ent
                entity = find_entity(new_entity)   #TODO: implement find_entity
                if DUMP_PACKET_ENTITIES:
                    print('entity delta update: id:{}, class:{}, serial:{}'.format(entity.nEntity,
                                                                                   entity.u_class,
                                                                                   entity.u_serial_num))
                read_new_entity(entity_bit_buffer, entity)
            elif update_type == 3:  # preserve ent
                if not as_delta:
                    raise ValueError('PreserveEnt on full update')     # right type of exception?
                if new_entity >= MAX_EDICTS:
                    raise ValueError('PreserveEnt: new_entity >= MAX_EDICTS')
                else:
                    if DUMP_PACKET_ENTITIES:
                        print('PreserveEnt: id:{}'.format(new_entity))

def handle_net_default(data_stream, size, cmd):
    """handles a non-special case, it might be slightly ugly"""
    types = [netmessages_public_pb2.CCNETMsg_NOP,
             netmessages_public_pb2.CNETMsg_Disconnect,
             netmessages_public_pb2.CNETMsg_File,
             netmessages_public_pb2.CNETMsg_Tick,
             netmessages_public_pb2.CNETMsg_StringCmd,
             netmessages_public_pb2.CNETMsg_SetConVar,
             netmessages_public_pb2.CNETMsg_SignonState,
             netmessages_public_pb2.CSVCMsg_ServerInfo,
             netmessages_public_pb2.CSVCMsg_SendTable,
             netmessages_public_pb2.CSVCMsg_ClassInfo,
             netmessages_public_pb2.CSVCMsg_SetPause,
             netmessages_public_pb2.CSVCMsg_CreateStringTable,
             netmessages_public_pb2.CSVCMsg_UpdateStringTable,
             netmessages_public_pb2.CSVCMsg_VoiceInit,
             netmessages_public_pb2.CSVCMsg_VoiceData,
             netmessages_public_pb2.CSVCMsg_Print,
             netmessages_public_pb2.CSVCMsg_Sounds,
             netmessages_public_pb2.CSVCMsg_SetView,
             netmessages_public_pb2.CSVCMsg_FixAngle,
             netmessages_public_pb2.CSVCMsg_CrosshairAngle,
             netmessages_public_pb2.CSVCMsg_BSPDecal,
             netmessages_public_pb2.CSVCMsg_UserMessage,
             netmessages_public_pb2.CSVCMsg_GameEvent,
             netmessages_public_pb2.CSVCMsg_PacketEntities,
             netmessages_public_pb2.CSVCMsg_TempEntities,
             netmessages_public_pb2.CSVCMsg_Prefetch,
             netmessages_public_pb2.CSVCMsg_Menu,
             netmessages_public_pb2.CSVCMsg_GameEventList,
             netmessages_public_pb2.CSVCMsg_GetCvarValue]
    msg = types[cmd]()
    msg.ParseFromString(read_bytes(data_stream, size))
    if cmd == 30:       # svc game event list
        # demo.game_event_list should be set here but does not exist
        # TODO: get a demo object and change this to demo.game_event_list
        GAME_EVENT_LIST.MergeFrom(msg)
    demo_msg_print(msg, size)

def handle_netmsg(data_stream, size, cmd):
    """handle the top level of netmsg and svcmsg parsing"""
    if cmd == 23:   # svc user message
        handle_svc_user_message(data_stream, size, cmd)
    elif cmd == 25:     # svc game event
        handle_svc_game_event(data_stream, size, cmd)
    elif cmd == 12:     # svc create string table
        handle_svc_create_string_table(data_stream, size, cmd)
    elif cmd == 13:     # svc update string table
        handle_svc_update_string_table(data_stream, size, cmd)
    elif cmd == 9:      # svc send table
        handle_svc_send_table(data_stream, size, cmd)
    elif cmd == 26:     # svc packet entities
        handle_svc_packet_entities(data_stream, size, cmd)
    else:
        handle_net_default(data_stream, size, cmd)

def dump_demo_packet(data_stream, length):
    """deals with some parsing of a demo packet"""
    while data_stream.bytepos < length:
        cmd = read_varint32(data_stream)
        size = read_varint32(data_stream)

        assert data_stream.bytepos + size < length

        # if cmd is 0-7 it is a netmsg, otherwise svcmsg
        # these are seperate functions in the C code, but they
        # seem to be identical-ish
        handle_netmsg(data_stream, size, cmd)
        
        # here the C code does a buf.SeekRelative(size*8), but I'm going to make an awful
        # assumption that the reading code already aligns to that and just ignore it

def handle_demo_packet(data_table_bytes):
    """parses a data packet"""
    read_cmd_info(data_table_bytes)
    read_sequence_info(data_table_bytes)    # result ignored

    data_table = read_bytes(data_table_bytes, NET_MAX_PAYLOAD)

    length = read_raw_data(data_table)
    dump_demo_packet(data_table, length)

def dump(demo_stream):
    """gets the information from the demo"""
    match_started = False
    demo_finished = False

    while not demo_finished:
        cmd, tick, player_slot = read_cmd_header(demo_stream)
        
        if DEBUG:
            print('cmd:{}, tick:{}, player_slot:{}'.format(cmd, tick, player_slot))

        current_tick = tick

        if tick == 1:
            #startup packet
            #handled same as tick type 2
            handle_demo_packet(data_table_bytes)

        elif tick == 2:
            #normal network packet
            #handled same as tick type 1
            handle_demo_packet(data_table_bytes)

        elif tick == 3:
            #synctick, doesn't seem to do anything
            pass
        
        elif tick == 4:
            #console command, nothing seems to be saved in c++
            #it might be interesting to do something with this at some point
            buf = read_raw_data(demo_stream)

        elif tick == 5:
            read_user_cmd(data_table_bytes)

        elif tick == 7:
            #stop tick
            demo_finished = True
            parse_data_table(data_table_bytes)

        elif tick == 8:
            #custom data, "blob of binary data
            pass

        elif tick == 9:
            #read a stringtable, somewhat confusing
            data_table_bytes = read_raw_data(demo_stream)
            
            dump_string_tables(data_table_bytes)

def main():
    """main method, currently opens test.dem, parses the header,
    and then tries and fails to parse the main body"""
    if DEBUG:
        pathtofile = 'test.dem'     # makes testing less tedious
    else:
        pathtofile = input('path to demo>')
    print('parsing {}'.format(pathtofile))
    demo_stream = ConstBitStream(filename=pathtofile)
    demo_info = get_demo_info(demo_stream)
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
    dump(demo_stream)

if __name__ == '__main__':
    main()
