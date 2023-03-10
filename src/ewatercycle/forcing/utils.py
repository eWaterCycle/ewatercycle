from pathlib import Path
from typing import Optional

from esmvalcore.experimental import CFG
from esmvalcore.experimental.config import Session


def _session(directory: Optional[str] = None) -> Optional[Session]:
    """When directory is set return a ESMValTool session that will write recipe
    output to that directory."""
    if directory is None:
        return None

    class TimeLessSession(Session):
        def __init__(self, output_dir: Path):
            super().__init__(CFG.copy())
            self.output_dir = output_dir

        @property
        def session_dir(self):
            return self.output_dir

    return TimeLessSession(Path(directory).absolute())
