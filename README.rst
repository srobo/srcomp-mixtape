SR Comp Mixtape
===============

|Build Status|

A service which plays tracks throughout a competition.

Usage
-----

Install the library using:

.. code:: shell

    pip install -U pip setuptools wheel
    pip install git+https://github.com/srobo/srcomp-mixtape


Development
-----------

**Install**:
``pip install -e .``

**Run checks**:
``./script/check``


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
- ``tracks`` defines the triggers and tracks to be played in a specific match, as a giant dictionary of the match number to track configuration.
- ``all`` defines the triggers and tracks to be played in *every* match, in the same format as a single match in ``tracks``.
- ``obs_studio`` defines the connection settings to an instance of OBS Studio
  which has the `obs-websocket plugin <https://github.com/Palakis/obs-websocket>`_
  installed. This requires the following nested keys:

  - ``port``: the websocket port for the (probably `4444`)
  - ``password``: the password for the websocket
  - ``source_name``: the name of the "Source" within OBS Studio that will play the videos.
    The source being controlled the option "Close file when inactive" needs to be set to allow the source to be changed when not active.
  - ``scene_name``: the name of the "Scene" within OBS Studio that contains the above Source.
    The scene being transitioned to needs "Transition Override > Fade" selected so there is a fade.
  - ``preload_time``: the period, in seconds, before a video is played that it should be loaded and transitioned to.

Track configuration
-------------------

The configuration for a track is a list of triggers, each of which is a dictionary containing the following keys:

- ``start`` is the time of the trigger, in seconds, relative to the game start time. Note: This value can be negative to represent actions before the start of the match. The limit is the pre-match time defined in the compstate schedule.

And either:

- ``filename`` is the path to a WAV file to play, relative to the mixtape directory.
- ``output_device`` is the Audio device to send the output to.
- ``group`` (optional) is the exclusivity group to assign this trigger to; only one sound from a given exclusivity group can be playing at a time.

Or:

- ``magicq_cue`` is the MagicQ cue ID to send.
- ``magicq_playback`` is the MagicQ playlist ID to send.

Or:

- ``obs_video`` is the path to a video file which should be played by OBS Studio.
  The track start corresponds to the point where the video begins playing.
  The video will be loaded and transitioned to ``preload_time`` seconds before this.


.. |Build Status| image:: https://circleci.com/gh/srobo/srcomp-mixtape.svg?style=svg
   :target: https://circleci.com/gh/srobo/srcomp-mixtape
