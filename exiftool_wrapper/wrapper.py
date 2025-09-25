import asyncio
import json
import os
import subprocess
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path
from typing import Any


class ExifToolWrapper:
    PROGRAM = "exiftool"
    BLOCKSIZE = 4096
    SENTINEL = b"{ready}"
    SENTINEL_LEN = len(SENTINEL)

    def __init__(self, common_args: Sequence[str] | None = None):
        self.common_args = common_args

    @cached_property
    def _pipe(self) -> subprocess.Popen:
        args = [self.PROGRAM, "-stay_open", "True", "-@", "-"]
        if self.common_args:
            args.append("-common_args")
            args.extend(self.common_args)

        pipe = subprocess.Popen(  # noqa: S603
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        return pipe

    @cached_property
    def _async_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    @staticmethod
    def _encode_args(args, *, encoding: str):
        return [
            arg.encode(encoding, errors="surrogateescape") if isinstance(arg, str) else arg
            for arg in args
        ]

    def process(self, *args: str | bytes | Path, encoding: str = "utf-8") -> bytes:
        args = (str(arg) if isinstance(arg, Path) else arg for arg in args)
        self._pipe.stdin.write(
            b"\n".join(self._encode_args(args, encoding=encoding)) + b"\n-execute\n"
        )
        self._pipe.stdin.flush()

        fd = self._pipe.stdout.fileno()
        output = b""

        sentinel_check_index = -self.SENTINEL_LEN - 2
        while not output[sentinel_check_index:].rstrip().endswith(self.SENTINEL):
            output += os.read(fd, self.BLOCKSIZE)

        return output.rstrip()[: -self.SENTINEL_LEN]

    def process_json_many(
        self, *args: str | bytes | Path, encoding: str = "utf-8"
    ) -> list[dict[str, Any]]:
        return json.loads(self.process("-j", *args).decode("utf-8"))

    def process_json(
        self, path: str | bytes | Path, *, args: Sequence[str] = (), encoding: str = "utf-8"
    ) -> dict[str, Any]:
        assert all(arg.startswith("-") for arg in args)  # noqa: S101
        args = (*tuple(args), path)
        return self.process_json_many(*args, encoding=encoding)[0]

    async def process_json_many_async(
        self, *args: str | bytes | Path, encoding: str = "utf-8"
    ) -> list[dict[str, Any]]:
        async with self._async_lock:
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: self.process_json_many(*args, encoding=encoding)
            )

    async def process_json_async(
        self, path: str | bytes | Path, *, args: Sequence[str] = (), encoding: str = "utf-8"
    ) -> dict[str, Any]:
        assert all(arg.startswith("-") for arg in args)  # noqa: S101
        args = (*tuple(args), path)
        return (await self.process_json_many_async(*args, encoding=encoding))[0]
