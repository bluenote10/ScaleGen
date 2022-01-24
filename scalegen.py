#!/usr/bin/env python

import os
from typing import Any, List

import midi
from typing_extensions import Literal

# We are using a high precision ticks-per-quarter (= PPQ) resolution
PPQ_RESOLUTION = 960


def get_note_length(numerator: int = 1, denominator: int = 4) -> int:
    return int(numerator / denominator * 4 * PPQ_RESOLUTION)


def render_midi(midifile: str, basename: str, delete_wave: bool = True) -> None:
    """
    Requires system packages: fluidsynth fluid-soundfont-gm lame
    http://wootangent.net/2010/11/converting-midi-to-wav-or-mp3-the-easy-way/
    """
    filename_mid = basename + ".mid"
    filename_wav = basename + ".wav"
    filename_mp3 = basename + ".mp3"
    midi.write_midifile(filename_mid, midifile)

    print("\n *** Rendering MIDI")
    os.system(
        "fluidsynth -F {} /usr/share/sounds/sf2/FluidR3_GM.sf2 {}".format(
            filename_wav,
            filename_mid,
        )
    )

    print("\n *** Converting to MP3")
    os.system(
        "lame --preset standard {} {}".format(
            filename_wav,
            filename_mp3,
        )
    )

    if delete_wave:
        os.system("rm {}".format(filename_wav))


class Note(object):
    def __init__(
        self, tick_from: float, tick_upto: float, pitch: int, velocity: int = 100
    ):
        self.tick_from = tick_from
        self.tick_upto = tick_upto
        self.pitch = pitch
        self.velocity = velocity
        assert tick_upto >= tick_from


Track = Literal["fg", "bg"]


class MidiData(object):
    def __init__(self) -> None:
        self.data_fg: List[Note] = []
        self.data_bg: List[Note] = []

    def add_note(self, track: Track, note: Note) -> None:
        if track == "fg":
            self.data_fg.append(note)
        elif track == "bg":
            self.data_bg.append(note)
        else:
            raise ValueError("Unknown track ID.")

    def extract_track_data(self) -> List[Any]:
        output = []
        for track in [self.data_fg, self.data_bg]:
            track_converted = MidiData.convert_track(track)
            output.append(track_converted)
        return output

    @staticmethod
    def convert_track(track: List[Note]) -> List[Any]:
        # Create pairs of on/off events
        events_timestamped = []
        for note in track:
            evt_on = midi.NoteOnEvent(
                tick=note.tick_from, pitch=note.pitch, velocity=note.velocity
            )
            evt_off = midi.NoteOffEvent(tick=note.tick_upto, pitch=note.pitch)
            events_timestamped.append((note.tick_from, evt_on))
            events_timestamped.append((note.tick_upto, evt_off))

        events_timestamped = sorted(events_timestamped)

        # Convert to relative times
        events = []
        pos = 0.0
        for timestamp, event in events_timestamped:
            delta = timestamp - pos
            event.tick = delta
            events.append(event)
            pos += delta

        # Add end-of-track
        evt_eot = midi.EndOfTrackEvent(tick=0)
        events.append(evt_eot)
        return events


def generate(track_data: List[Any], bpm: float, basename: str) -> None:
    midifile = midi.Pattern(resolution=PPQ_RESOLUTION)

    # Add a tempo track
    track_tempo = midi.Track()
    midifile.append(track_tempo)

    evt_tempo = midi.SetTempoEvent(bpm=bpm)
    track_tempo.append(evt_tempo)

    # Add tracks from trackdata
    for track in track_data:
        midifile.append(track)

    print(midifile)
    render_midi(midifile, basename)


Pattern = List[int]


def get_start_pitches(
    pattern: Pattern, low: int = midi.A_3, high: int = midi.C_6
) -> List[int]:
    max_delta = max(pattern)
    return list(range(low, high - max_delta + 1))


def generator_major_triad(low: int = midi.A_3, high: int = midi.C_6) -> MidiData:
    data = MidiData()

    note_length = get_note_length()
    pattern = [0, 4, 7, 12, 7, 4, 0]

    start_pitches = get_start_pitches(pattern, low, high)

    pos = 0
    for start_pitch in start_pitches:
        data.add_note("bg", Note(pos, pos + note_length * 8, start_pitch - 12))
        for delta in pattern:
            data.add_note("fg", Note(pos, pos + note_length, start_pitch + delta))
            pos += note_length
        pos += note_length

    return data


def generator_major_scale(low: int = midi.A_3, high: int = midi.C_6) -> MidiData:
    data = MidiData()

    note_length = get_note_length(1, 8)
    pattern = [0, 2, 4, 5, 7, 9, 11, 12, 11, 9, 7, 5, 4, 2, 0]

    start_pitches = get_start_pitches(pattern, low, high)

    pos = 0
    for start_pitch in start_pitches:
        data.add_note("bg", Note(pos, pos + note_length * 16, start_pitch - 12))
        for delta in pattern:
            data.add_note("fg", Note(pos, pos + note_length, start_pitch + delta))
            pos += note_length
        pos += note_length

    return data


def main() -> None:
    generate(generator_major_triad().extract_track_data(), 120, "major_triad")
    generate(generator_major_scale().extract_track_data(), 90, "major_scale")


if __name__ == "__main__":
    main()
