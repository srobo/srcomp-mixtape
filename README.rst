SR Comp Mixtape
===============

A service which plays tracks throughout a competition.

Configuration
-------------

A configuration of tracks and triggers to play during a competition is called
a ``mixtape``. A mixtape is a directory containing:

- A configuration file, ``playlist.yaml``, which defines trigger points,
- Tracks to play, in 16-bit, 44.1kHz uncompressed WAV format.

Using uncompressed audio is unfortunately necessary due to the nondeterministic
time it takes to decode compressed audio, which can throw off timings.

``playlist.yaml`` contains the following top-level keys:

- ``magicq`` defines the MagicQ connection settings, for automatic triggering of lights.
- ``tracks`` defines the triggers and tracks to be played in each match, as a giant dictionary of match number to track configuration.
- ``all`` defines the triggers and tracks to be played in *every* match, in the same format as a single match in ``tracks``.

Track configuration
-------------------

The configuration for a track is a list of triggers, each of which is a dictionary containing the following keys:

- ``start`` is the time of the trigger, relative to the game start time.
- ``filename`` is the path to a WAV file to play, relative to the mixtape directory.
- ``output_device`` is the Audio device to send the output to.
- ``magicq_cue`` is the MagicQ cue ID to send.
- ``magicq_playlist`` is the MagicQ playlist ID to send.
- ``group`` (optional) is the exclusivity group to assign this trigger to; only one sound from a given exclusivity group can be playing at a time.
