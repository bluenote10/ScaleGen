#!/usr/bin/env python

import os
from typing import Any, List

import pretty_midi
from typing_extensions import Literal

# We are using a high precision ticks-per-quarter (= PPQ) resolution
PPQ_RESOLUTION = 960


def _render_midi(
    midifile: pretty_midi.PrettyMIDI,
    basename: str,
    delete_wave: bool = True,
) -> None:
    """
    Requires system packages: fluidsynth fluid-soundfont-gm lame
    http://wootangent.net/2010/11/converting-midi-to-wav-or-mp3-the-easy-way/
    """
    filename_mid = basename + ".mid"
    filename_wav = basename + ".wav"
    filename_mp3 = basename + ".mp3"
    midifile.write(filename_mid)

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
    def __init__(self, bpm: float) -> None:
        self.bpm = bpm
        self.data_fg: pretty_midi.Instrument = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
        )
        self.data_bg: pretty_midi.Instrument = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
        )

    def _beat_to_abs_time(self, beat: float) -> float:
        return beat * 60 / self.bpm

    def add_note(self, track: Track, note: Note) -> None:
        # Note that pretty_midi always uses absolute time for notes and basically
        # ignores the tempo setting of the file. Therefore we must to manually convert
        # from "beat time" to absolute time.
        pretty_note = pretty_midi.Note(
            velocity=100,
            pitch=note.pitch,
            start=self._beat_to_abs_time(note.tick_from),
            end=self._beat_to_abs_time(note.tick_upto),
        )
        if track == "fg":
            self.data_fg.notes.append(pretty_note)
        elif track == "bg":
            self.data_bg.notes.append(pretty_note)
        else:
            raise ValueError("Unknown track ID.")

    def convert_to_midi_file(self) -> pretty_midi.PrettyMIDI:
        midi_file = pretty_midi.PrettyMIDI(
            resolution=PPQ_RESOLUTION, initial_tempo=self.bpm
        )
        midi_file.instruments.append(self.data_fg)
        midi_file.instruments.append(self.data_bg)
        return midi_file

    def write_midi_file(self, output_basename: str) -> None:
        midi_file = self.convert_to_midi_file()
        _render_midi(midi_file, output_basename)


Pattern = List[int]


def get_start_pitches(
    pattern: Pattern, low: int, high: int, cycle_up_down: bool = True
) -> List[int]:
    min_delta = min(pattern)
    max_delta = max(pattern)

    lowest = low - min_delta
    highest = high - max_delta

    if not cycle_up_down:
        return list(range(lowest, highest + 1))
    else:
        return list(range(lowest, highest + 1)) + list(reversed(range(lowest, highest)))


def generator_major_triad(
    bpm: float = 120.0,
    low: int = pretty_midi.note_name_to_number("A3"),
    high: int = pretty_midi.note_name_to_number("C6"),
) -> MidiData:
    data = MidiData(bpm)

    note_length = 1.0
    pattern = [0, 4, 7, 12, 7, 4, 0]

    start_pitches = get_start_pitches(pattern, low, high)

    pos = 0.0
    for start_pitch in start_pitches:
        data.add_note("bg", Note(pos, pos + note_length * 8, start_pitch - 12))
        for delta in pattern:
            data.add_note("fg", Note(pos, pos + note_length, start_pitch + delta))
            pos += note_length
        pos += note_length

    return data


def generator_major_scale(
    bpm: float = 90.0,
    low: int = pretty_midi.note_name_to_number("A3"),
    high: int = pretty_midi.note_name_to_number("C6"),
) -> MidiData:
    data = MidiData(bpm)

    note_length = 1.0
    pattern = [0, 2, 4, 5, 7, 9, 11, 12, 11, 9, 7, 5, 4, 2, 0]

    start_pitches = get_start_pitches(pattern, low, high)

    pos = 0.0
    for start_pitch in start_pitches:
        data.add_note("bg", Note(pos, pos + note_length * 16, start_pitch - 12))
        for delta in pattern:
            data.add_note("fg", Note(pos, pos + note_length, start_pitch + delta))
            pos += note_length
        pos += note_length

    return data


def main() -> None:
    generator_major_triad().write_midi_file("major_triad")
    generator_major_scale().write_midi_file("major_scale")


if __name__ == "__main__":
    main()
