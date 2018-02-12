# DGX-505 MIDI information and other miscellany

## MIDI Implementation Chart Info
Some of this information comes from the MIDI Implementation chart
located on pages 110–113 of my multilingual copy of the DGX-505 manual
(pages 105–106 of the online English copy).
See those pages for more information, such as what is *not* recognised.

Some of this is from me experimenting with what messages are transmitted.

In this document, `00` denotes hexadecimal, 00 decimal.

NOTE: According to Note 1 on pg. 113, the DGX-505 functions as a tone generator
and incoming data does not affect the panel voices/settings, with the exception
of MIDI Master Tuning and Reverb/Chorus type messages.

The state of the panel can also be affected by Local ON/OFF messages and
time control Start/Stop messages (when using External Clock).

### Channels
MIDI has 16 channels, numbered 1–16 for human consumption but 0–15 (`0`–`F`)
internally. This makes talking about them a bit confusing, so I'm going to
only use the hexadecimal notation.

Since incoming data does not affect the panel settings, we can think of
two separate sets of channels:
one set for the data coming in over the MIDI port,
and the other for the data generated by the DGX-505 itself from the keyboard
or from playback when transmitted out the MIDI port.
These two sets are entirely separate and do not affect each other (see note 1
after the chart in the manual); changing the voice using messages for channel
`0` affects the voice the DGX-505 uses when sounding incoming messages
for channel `0` but does not affect the voice used when sounding from the
keyboard directly , even though the notes from the keyboard are also sent out
using channel `0`.

It can be useful to experiment by turning LOCAL off (disabling the keyboard
from activating the tone generator directly), then connecting the DGX-505
MIDI output to its input.

When output from the DGX-505, the keyboard voices use the first three channels:
* Main voice:  `0`
* Dual voice:  `1`
* Split voice: `2`

Harmony only affects the Main voice, so the Harmony notes also use `0`.

Style output uses channels `8` and `9` for percussion, and `A`, through `F`
for accompaniment.

This leaves channels 3, 4, 5, 6, 7.
Actually I'm not sure how exactly the song playback goes. Must check that out.



### Basic Channel
Default 1–16 only, no Changed.

### Mode
There's only one Mode 3: OMNI OFF, POLY

### Note number
0 to 127. True Voice.

Note numbers run from 0–127 (`00`–`7F`).
The lowest key on the DGX-505, A-1, is 21 (`15`), the highest, C7, is 108
(`63`). Middle C, C3, is 60 (`3C`).
The numbers transmitted are affected by the Octave and Transpose settings,
which allows all possible notes to be played on the keyboard.
Interestingly, if the shifted notes overflow past 0 or 127, they are
transposed an octave to keep them within range.

### Note ON
* `9n`, velocity=1–127
* velocity=0 functions as a Note OFF.

### Note OFF
Note OFF (`8n`) messages do in fact work,
but the velocity parameter is ignored.

### Pitch Bend
Pitch bend messages are transmitted when the pitch bend wheel is used.
They are of the format `En ll mm`, where `n` is the channel, and `ll mm` is
some sort of little-endian offset number ranging from -8192 (`00 00`), through
zero (`00 40`), up to 8191 (`7F 7F`).
The formula is (`ll` + `80` * `mm`) - `200`.


### Control Change messages
Control change messages have the form `Bn cc dd`, where `n` is the channel,
`cc` is the control, `dd` is the value.

### Setting the voice
The voice is set by specifying a bank and program.
These are listed for each voice in the back of the manual.
The bank is set with two control change messages (0 & 32 / `00` & `20`),
one for each byte; the program is set with a program change message `Cn`.
The voice does not change until the program is set.

Program change numbers are listed as 1–128, but the numbers in the
messages are actually 0–127 (`00`–`7F`). We all love conflicting
indexing conventions.

(note: there is an anomaly in the voice list.
On pg.100, the MIDI Program change for Steel Drums has an extra leading zero.
This can be ignored. The real value is 115,
which means 114 in the actual message, of course)

#### Bank Select
* Control 0 sets the MSB: `Bn 00 mm`
* Control 32 sets the LSB: `Bn 20 ll`

#### Program Change
`Cn xx`

For example, voice no. 153, 'Harpsichord KSP', has Bank MSB 0, LSB 1,
and program 7; to set channel `0` to this voice we use the messages
`B0 00 00` `B0 20 01` `C0 06`.

### Voice Volume
Control 7: `Bn 07 xx`

### Voice Pan
Control 10: `Bn 0A xx`

### Voice Reverb Level
Control 91: `Bn 5B xx`

### Voice Chorus Level
Control 93: `Bn 5D xx`

### Pedal Sustain
Control 64:

* value 127 on pedal down: `Bn 40 7F`
* value 0 on pedal up: `Bn 40 00`

More generally, values 63 and below act like 0, 64 and above like 127.

### Panel Sustain
Using the Panel Sustain function will emit Control 72:

* value 110 for sustain ON: `Bn 48 6E`
* value 64 for sustain OFF: `Bn 48 40`

More generally, this parameter is really the 'Release Time' according to
the chart, and can actually be set to any value 0–127:
#### Release Time
Control 72: `Bn 48 xx`

### Other Control Change Messages
These cannot be transmitted directly from the keyboard or panel, but
may be transmitted by Harmony or Song/Style playback.

#### Modulation wheel
Control 1: `Bn 01 xx`
- Makes wobbly sounds.

#### Expression
Control 11: `Bn 0B xx`

#### Portamento Control
Control 84: `Bn 54 xx`

#### Harmonic Content
Control 71: `Bn 47 xx`

#### Attack Time
Control 73: `Bn 49 xx`
- This is like the opposite counterpart of Release time, I think

#### Brightness
Control 74: `Bn 4A xx`

### RPN
Used for more complicated settings.

#### RPN Inc, Dec (96, 97)

#### RPN LSB / MSB
* MSB set with Control 101: `Bn 65 mm`
* LSB set with Control 100: `Bn 64 ll`

#### Data Entry
* MSB set with Control 6: `Bn 06 mm`
* LSB set with Control 38: `Bn 26 mm`


#### Pitch Bend Range
Pitch Bend Range uses RPN `00 00`, with the value as MSB.

For example, a pitch bend range of 8 on channel `0` is set with the messages
  `B0 65 00` `B0 64 00` `B0 06 08`

The panel's Pitch Bend Range setting covers 1–12 for the three keyboard voices
on channels `0`, `1`, `2`; messages for the tone generator can use 0–24 and
set the range independently for each channel.


### System Real Time
#### Clock
Clock messages (`F8`) are transmitted when External Clock is OFF.

#### Commands
There are two messages implemented, Start (`FA`) and Stop (`FC`).
These are transmitted at the start and end of song/style playback.
Start and Stop messages can also be received when External Clock is ON.

### Aux Messages

#### All Sound OFF (120, 126, 127)

#### Reset All Cntrls (121)

#### Local ON/OFF
Control 122:

* Local ON: `Bn 7A 7F`
* Local OFF: `Bn 7A 00`

(The channel parameter `n` is ignored.)

Like the Pedal Sustain, values 63 and below are OFF; 64 and above are ON.

#### All Notes OFF (123–125)

#### Active Sense

### System Exclusive

#### GM System ON: `F0 7E 7F 09 01 F7`
* "Automatically restores all default settings except Master Tuning"   

#### MIDI Master Volume: `F0 7F 7F 04 01 ll mm F7`
* Changes volume of all channels
* `mm` values used, `ll` ignored.

#### MIDI Master Tuning: `F0 43 1n 27 30 00 00 mm ll cc F7`
* Changes tuning of all channels
* `mm ll` used, defaults to `08 00`. `n` and `cc` ignored.

#### Reverb Type: `F0 43 1n 4C 02 01 00 mm ll F7`
* `mm ll` are the MSB and LSB respectively.
* MSB types:
  * `00`, `05`–`7F`: 10(Off)
  * `01`: 01(Hall1)
  * `02`: ---(Room)
  * `03`: ---(Stage)
  * `04`: ---(Plate)
* Specific (MSB LSB) types:
  * `01 00`: 01(Hall1)
  * `01 10`: 02(Hall2)
  * `01 11`: 03(Hall3)
  * `02 11`: 04(Room1)
  * `02 13`: 05(Room2)
  * `03 10`: 06(Stage1)
  * `03 11`: 07(Stage2)
  * `04 10`: 08(Plate1)
  * `04 11`: 09(Plate2)
* It appears that when an LSB corresponds to no specific type specified above,
  it is as if the LSB was `00`. This means that most fall back to the generic
  effects that appear as ---(Room) etc, with the exception of Hall, which
  falls back to 01(Hall1).

#### Chorus Type `F0 43 1n 4C 02 01 20 mm ll F7`
* `mm ll` are MSB and LSB respectively
* MSB types:
  * `00`–`3F`, `44`–`7F`: 5(Off)
  * `40`: ---(Thru)
  * `41`: ---(Chorus)
  * `42`: ---(Celeste)
  * `43`: ---(Flanger)
* Specific (MSB LSB) types:
  * `42 11`: 1(Chorus1)
    - (I guess Celeste is a type of Chorus?)
  * `41 02`: 2(Chorus2)
  * `43 08`: 3(Flanger1)
  * `43 11`: 4(Flanger2)
* The same LSB fallback applies.