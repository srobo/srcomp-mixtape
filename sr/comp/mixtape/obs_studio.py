import threading
from types import TracebackType
from typing import Generic, Optional, Type, TypeVar

from obswebsocket import obsws, requests  # type: ignore[import]

T = TypeVar('T')

PLAY, PAUSE = False, True


class Guarded(Generic[T]):
    """
    A generic mechanism to protect an object which may need to be accessed from
    several threads.
    """

    def __init__(self, value: T) -> None:
        self._value = value
        self._lock = threading.Lock()

    def __enter__(self) -> T:
        self._lock.__enter__()
        return self._value

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return self._lock.__exit__(exc_type, exc_val, exc_tb)


class OBSStudioController:
    """
    Connect to an instance of OBS Studio via the obs-websocket plugin.

    See https://github.com/Palakis/obs-websocket for the plugin's details.
    """

    def __init__(
        self,
        port: int,
        password: str,
        source: str,
        scene: str,
        preroll_time: float,
    ) -> None:
        websocket = obsws('localhost', port, password)
        websocket.connect()

        self.source_name = source
        self.scene_name = scene
        self.preroll_time = preroll_time
        self.video_info = websocket.call(requests.GetVideoInfo())

        # Our play_video method is going to be called from one of the (possibly
        # many) worker threads which the scheduler will use. Guard it against
        # concurrent access.
        self.websocket = Guarded(websocket)

    def load_video(self, filename: str) -> None:
        with self.websocket as websocket:
            websocket.call(requests.SetSourceSettings(
                self.source_name,
                {
                    'local_file': filename,
                    'looping': False,
                    'restart_on_activate': False,
                    'clear_on_media_end': False,
                },
            ))

            websocket.call(requests.SetSceneItemProperties(
                {'name': self.source_name},
                # Setting the bounds here means that the media will fill the canvas,
                # preserving its aspect ratio.
                bounds={
                    'type': 'OBS_BOUNDS_SCALE_INNER',
                    'x': self.video_info.getBaseWidth(),
                    'y': self.video_info.getBaseHeight(),
                },
            ))

            websocket.call(requests.PlayPauseMedia(self.source_name, PAUSE))
            websocket.call(requests.ScrubMedia(self.source_name, 0))

            websocket.call(requests.SetCurrentScene(self.scene_name))

    def play_video(self) -> None:
        with self.websocket as websocket:
            websocket.call(requests.PlayPauseMedia(self.source_name, PLAY))

    def transition_scene(self, scene_name: str) -> None:
        with self.websocket as websocket:
            websocket.call(requests.SetCurrentScene(scene_name))
