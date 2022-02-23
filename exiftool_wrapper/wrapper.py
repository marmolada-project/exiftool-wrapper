import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


class ExifToolWrapper:

    PROGRAM = "exiftool"
    BLOCKSIZE = 4096
    SENTINEL = b"{ready}"
    SENTINEL_LEN = len(SENTINEL)

    def __init__(self, common_args: Optional[Sequence[str]] = None):
        self.common_args = common_args

    @property
    def pipe(self) -> subprocess.Popen:
        if not hasattr(self, "_pipe"):
            self._pipe = self._create_pipe()
        return self._pipe

    def _create_pipe(self) -> subprocess.Popen:
        args = [self.PROGRAM, "-stay_open", "True", "-@", "-"]
        if self.common_args:
            args.append("-common_args")
            args.extend(self.common_args)

        pipe = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        return pipe

    @staticmethod
    def _encode_args(args, *, encoding: str):
        return [
            arg.encode(encoding, errors="surrogateescape") if isinstance(arg, str) else arg
            for arg in args
        ]

    def process(self, *args: Union[str, bytes, Path], encoding: str = "utf-8") -> bytes:
        args = (str(arg) if isinstance(arg, Path) else arg for arg in args)
        self.pipe.stdin.write(
            b"\n".join(self._encode_args(args, encoding=encoding)) + b"\n-execute\n"
        )
        self.pipe.stdin.flush()

        fd = self.pipe.stdout.fileno()
        output = b""

        sentinel_check_index = -self.SENTINEL_LEN - 2
        while not output[sentinel_check_index:].rstrip().endswith(self.SENTINEL):
            output += os.read(fd, self.BLOCKSIZE)

        return output.rstrip()[: -self.SENTINEL_LEN]

    def process_json_many(
        self, *args: Union[str, bytes, Path], encoding: str = "utf-8"
    ) -> List[Dict[str, Any]]:
        return json.loads(self.process("-j", *args).decode("utf-8"))

    def process_json(
        self, path: Union[str, bytes, Path], encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        return self.process_json_many(path, encoding=encoding)[0]
