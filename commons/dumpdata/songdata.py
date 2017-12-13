import collections
import struct

from ..util import slicebyn, boolean_bitarray_tuple, lazy_readonly_property
from ..exceptions import MalformedDataError, NotRecordedError
from .messages import DumpSection


class SongDumpSection(DumpSection):
    """
    Container for all the useful data in a song section of a bulk dump
    """
    SECTION_BYTE = 0x0A
    SECTION_NAME = "Song data"
    EXPECTED_COUNT = 39
    EXPECTED_RUN = 76904

    @lazy_readonly_property
    def songs(self):
        return SongData(self.data)

    def _cereal(self):
        return self.songs._cereal()


class SongData(collections.abc.Sequence):

    SONGS_OFFSET = 0x00
    MYSTERY_SLICE = slice(0x01, 0x15D)
    TRACKS_SLICE = slice(0x15D, 0x167)
    SONG_DURATION_SLICE = slice(0x167, 0x17B)
    TRACK_DURATION_SLICE = slice(0x17B, 0x1F3)
    PRESETSTYLE_SLICE = slice(0x1F3, 0x22F)
    BEGINNING_BLOCKS_SLICE = slice(0x22F, 0x24D)
    NEXT_BLOCKS_SLICE = slice(0x24D, 0x2CF)
    START_MARKER_SLICE = slice(0x2CF, 0x2D5)
    BLOCK_DATA_SLICE = slice(0x2D5, 0x106D5)
    END_MARKER_SLICE = slice(0x106D5, None)

    EXPECTED_SIZE = 0x106DB

    PRESETSTYLE = b'PresetStyle\0'*5
    MARKER = b'PK0001'

    def _message_format_checks(self):
        if len(self.data) != self.EXPECTED_SIZE:
            raise MalformedDataError("Data wrong length!")
        presetstyle = self.data[self.PRESETSTYLE_SLICE]
        startmarker = self.data[self.START_MARKER_SLICE]
        endmarker = self.data[self.END_MARKER_SLICE]
        if not ((startmarker == endmarker == self.MARKER) and
                (presetstyle == self.PRESETSTYLE)):
            raise MalformedDataError("Invalid format")
        if (self.data[self.SONGS_OFFSET] >= (1 << 5)
                or any(x >= (1 << 6) for x in self.data[self.TRACKS_SLICE])):
            raise MalformedDataError("Unexpected high bits in the fields")

    def __init__(self, data):
        """
        data = the concatenated payload data.
        songs are available through the songs attribute.
        """
        self.data = data
        self._message_format_checks()

        # song data
        self._song_field = boolean_bitarray_tuple(data[self.SONGS_OFFSET], 5)
        self._track_fields = [boolean_bitarray_tuple(x, 6)
                              for x in data[self.TRACKS_SLICE]]
        self._song_durations = struct.unpack('>5I',
                                             data[self.SONG_DURATION_SLICE])
        self._track_durations = list(slicebyn(
            struct.unpack('>30I', data[self.TRACK_DURATION_SLICE]), 6))

        self._track_beginning_blocks = list(slicebyn(
            data[self.BEGINNING_BLOCKS_SLICE], 6))

        self._block_system = SongDataBlockSystem(
            data[self.NEXT_BLOCKS_SLICE], data[self.BLOCK_DATA_SLICE])

        self._mystery = self.data[self.MYSTERY_SLICE]

        self._songs = [None] * 5

    def __getitem__(self, key):
        """
        Get the UserSong object.
        Note that we use zero based indexing, so UserSong1 corresponds to [0]
        and so on.
        Negative indices not supported, because why would you need that.
        """
        if self._songs[key] is None:
            self._songs[key] = UserSong(
                self._block_system, key+1,
                self._song_field[key], self._song_durations[key],
                self._track_fields[key], self._track_durations[key],
                self._track_beginning_blocks[key])
        return self._songs[key]

    def __len__(self, key):
        return len(self._songs)  # 5
    # The abstract base class Sequence takes care of the rest.

    # cereal!
    def _cereal(self):
        return [song._cereal() for song in self]


class SongDataBlockSystem(object):

    BLOCK_COUNT = 0x82
    BLOCK_SIZE = 0x200

    def __init__(self, next_blocks_table, block_data):
        self._next_blocks_table = next_blocks_table
        self._block_data = block_data

    def get_block_data(self, n):
        """
        Returns the specified block data of block n
        """
        if 1 <= n <= self.BLOCK_COUNT:
            end = self.BLOCK_SIZE * n
            start = end - self.BLOCK_SIZE
            return self._block_data[start:end]
        else:
            raise IndexError("Invalid index: {}".format(n))

    def get_next_block_number(self, n):
        """
        Returns the number of the block following block n
        """
        if n < 1:
            raise IndexError("Invalid index: {}".format(n))
        return self._next_blocks_table[n-1]

    def _block_data_iter(self, start_block, length):
        """Yields data blocks up to length from start_block"""
        num = start_block
        rem = length
        while rem > 0:
            if num == 0xFF:
                raise MalformedDataError("ran out too early")
            elif num == 0x00:
                raise MalformedDataError("referenced empty block")
            block = self.get_block_data(num)
            if rem < self.BLOCK_SIZE:
                block = block[:rem]
            rem -= len(block)
            num = self.get_next_block_number(num)
            yield block

    def get_track_blocks(self, start_block):
        """
        Gets a track chunk's size and blocks from its starting block number.
        MalformedDataError raised if chunk is invalid somehow
        returns (size, blocks), where:
        size is the total number of bytes in the chunk (including header)
        blocks is a list of the blocks (as memoryviews, with the last one
        truncated appropriately for the chunk size)
        """
        try:
            block = self.get_block_data(start_block)
        except IndexError:
            raise MalformedDataError("Invalid starting block")
        tag, dlength = struct.unpack_from('>4sL', block, 0)
        if tag != b'MTrk':
            raise MalformedDataError("Chunk start not found")
        size = dlength + 8
        blocks = list(self._block_data_iter(start_block, size))
        return size, blocks


class UserSong(object):
    """
    Represents one UserSong and associated data and metadata
    """

    UserSongTrack = collections.namedtuple(
        "UserSongTrack", "track name active duration size blocks")

    def __init__(self, block_system, number, active, duration,
                 tracks_active, tracks_duration, start_blocks):
        self.number = number
        self.active = active
        self.duration = duration

        self.name = "User Song {}".format(number)

        self._tracks = []
        # transpose the last track to first so that
        # index 0 = time/chord track A, index 1 = track 1 etc
        TRACK_NAMES = ('Track 1', 'Track 2', 'Track 3',
                       'Track 4', 'Track 5', 'Track A')
        for i in range(-1, 5):
            start_block = start_blocks[i]
            if start_block == 0xFF:
                size = 0
                blocks = None
            else:
                size, blocks = block_system.get_track_blocks(start_block)
            track = self.UserSongTrack(i+1, TRACK_NAMES[i],
                                       tracks_active[i], tracks_duration[i],
                                       size, blocks)
            self._tracks.append(track)

        self._datatracks = [track for track in self._tracks
                            if track.blocks is not None]
        if self._datatracks:
            self.size = 14 + sum(track.size for track in self._datatracks)
        else:
            self.size = 0

    def print_info(self):
        """
        Prints the recorded (active) status, duration (in measures),
        and size (in bytes) for the song overall and each track within, in a
        table.
        Note that Track A can still have data even if not recorded,
        as the track is also used as the time track for the whole song.
        """
        columns = "{:>12} {!s:>10} {:>10} {:>10}".format
        print(columns("", "Recorded", "Duration", "Size"))
        for item in (self, *self._tracks):
            print(columns(item.name, item.active, item.duration, item.size))

    def _midi_blocks_iter(self):
        if not self._datatracks:
            raise NotRecordedError("Song not recorded")
        header = struct.pack('>4sL3H',
                             b'MThd', 6, 1, len(self._datatracks), 96)
        yield header
        for track in self._datatracks:
            yield from track.blocks

    @lazy_readonly_property
    def midi(self):
        """The MIDI file, as bytes."""
        return b''.join(self._midi_blocks_iter())

    def _cereal(self):
        return collections.OrderedDict([
            ('number', self.number),
            ('name', self.name),
            ('active', self.active),
            ('duration', self.duration),
            ('size', self.size),
            ('tracks', [collections.OrderedDict([
                ('track', track.track),
                ('name', track.name),
                ('active', track.active),
                ('duration', track.duration),
                ('size', track.size)
            ]) for track in self._tracks])
        ])