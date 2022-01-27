#!/usr/bin/env python

import os
from typing import Any, List

import pretty_midi
from typing_extensions import Literal

# We are using a high precision ticks-per-quarter (= PPQ) resolution
PPQ_RESOLUTION = 960


# -----------------------------------------------------------------------------
# Pattern helpers
# -----------------------------------------------------------------------------

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


def close_pattern(pattern: Pattern) -> Pattern:
    return pattern + pattern[-2::-1]


# -----------------------------------------------------------------------------
# Midi generator wrapper
# -----------------------------------------------------------------------------


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


TrackId = Literal["fg", "bg"]


class Generator(object):
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

    def add_note(self, track_id: TrackId, note: Note) -> None:
        # Note that pretty_midi always uses absolute time for notes and basically
        # ignores the tempo setting of the file. Therefore we must to manually convert
        # from "beat time" to absolute time.
        pretty_note = pretty_midi.Note(
            velocity=100,
            pitch=note.pitch,
            start=self._beat_to_abs_time(note.tick_from),
            end=self._beat_to_abs_time(note.tick_upto),
        )
        if track_id == "fg":
            self.data_fg.notes.append(pretty_note)
        elif track_id == "bg":
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


# -----------------------------------------------------------------------------
# Generators
# -----------------------------------------------------------------------------


def generator_major_triad(
    bpm: float = 120.0,
    low: int = pretty_midi.note_name_to_number("A3"),
    high: int = pretty_midi.note_name_to_number("C6"),
) -> Generator:
    data = Generator(bpm)

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
) -> Generator:
    data = Generator(bpm)

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


def generator_scale_with_triad_opener(
    pattern: Pattern,
    bpm: float = 140.0,
    low: int = pretty_midi.note_name_to_number("E2"),
    high: int = pretty_midi.note_name_to_number("G4"),
    do_close_pattern: bool = True,
) -> Generator:
    if do_close_pattern:
        pattern = close_pattern(pattern)

    note_length = 1.0
    time_per_loop = (
        (len(pattern) + 3) * note_length * 60 / bpm
    )  # 3 because start pitch + triad + break
    print(
        f"Time per loop: {time_per_loop:.1f} sec / Loops per minute: {60 / time_per_loop:.1f}"
    )

    start_pitches = get_start_pitches(pattern, low, high)
    print(f"Total start pitches: {len(start_pitches)}")

    data = Generator(bpm)
    pos = 0.0
    for start_pitch in start_pitches:
        # 1. start pitch
        data.add_note("fg", Note(pos, pos + note_length, start_pitch))
        pos += note_length

        # 2. the triad
        data.add_note("fg", Note(pos, pos + note_length, start_pitch))
        data.add_note("fg", Note(pos, pos + note_length, start_pitch + pattern[2]))
        data.add_note("fg", Note(pos, pos + note_length, start_pitch + pattern[4]))
        pos += note_length

        for delta in pattern:
            data.add_note("fg", Note(pos, pos + note_length, start_pitch + delta))
            pos += note_length

        # break in between loops
        pos += note_length

    return data


def main() -> None:
    generate_basics = False
    if generate_basics:
        generator_major_triad().write_midi_file("major_triad")
        generator_major_scale().write_midi_file("major_scale")

    generate_modes = False
    if generate_modes:
        generator_scale_with_triad_opener(
            [0, 2, 4, 6, 7, 9, 11, 12],
        ).write_midi_file("scale_plain_lydian")
        generator_scale_with_triad_opener(
            [0, 2, 4, 5, 7, 9, 11, 12],
        ).write_midi_file("scale_plain_ionian")
        generator_scale_with_triad_opener(
            [0, 2, 4, 5, 7, 9, 10, 12],
        ).write_midi_file("scale_plain_mixolydian")
        generator_scale_with_triad_opener(
            [0, 2, 3, 5, 7, 9, 10, 12],
        ).write_midi_file("scale_plain_dorian")
        generator_scale_with_triad_opener(
            [0, 2, 3, 5, 7, 8, 10, 12],
        ).write_midi_file("scale_plain_aeolian")
        generator_scale_with_triad_opener(
            [0, 1, 3, 5, 7, 8, 10, 12],
        ).write_midi_file("scale_plain_phrygian")
        generator_scale_with_triad_opener(
            [0, 1, 3, 5, 6, 8, 10, 12],
        ).write_midi_file("scale_plain_locrian")

    generate_long_scale = False
    if generate_long_scale:
        long_scale_pattern = [0, 4, 7, 12, 16, 19, 17, 14, 11, 7, 5, 2, 0]
        generator_scale_with_triad_opener(
            long_scale_pattern,
            bpm=160,
            low=pretty_midi.note_name_to_number("Eb2"),
            high=pretty_midi.note_name_to_number("A4"),
            do_close_pattern=False,
        ).write_midi_file("long_scale_middle")
        generator_scale_with_triad_opener(
            long_scale_pattern,
            bpm=160,
            low=pretty_midi.note_name_to_number("Eb2"),
            high=pretty_midi.note_name_to_number("C#4"),
            do_close_pattern=False,
        ).write_midi_file("long_scale_low")
        generator_scale_with_triad_opener(
            long_scale_pattern,
            bpm=160,
            low=pretty_midi.note_name_to_number("B2"),
            high=pretty_midi.note_name_to_number("A4"),
            do_close_pattern=False,
        ).write_midi_file("long_scale_high")

    generate_chromatic = True
    if generate_chromatic:
        chromatic_pattern = list(range(8))
        generator_scale_with_triad_opener(
            chromatic_pattern,
            bpm=160,
            low=pretty_midi.note_name_to_number("Eb2"),
            high=pretty_midi.note_name_to_number("F3"),
        ).write_midi_file("chromatic_low")
        generator_scale_with_triad_opener(
            chromatic_pattern,
            bpm=160,
            low=pretty_midi.note_name_to_number("F3"),
            high=pretty_midi.note_name_to_number("G4"),
        ).write_midi_file("chromatic_high")


if __name__ == "__main__":
    main()
