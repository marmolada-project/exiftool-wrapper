import asyncio
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from PIL import ExifTags, Image

from exiftool_wrapper.wrapper import ExifToolWrapper

TAG_NAMES_TO_IDS = {value: key for key, value in ExifTags.TAGS.items()}


def create_image_file(
    parent_dir: Path, fname: str, tags: dict[str, Any], dims: (int, int) = (32, 32)
) -> Path:
    img_path = parent_dir / fname
    img = Image.new("RGB", dims)
    exif = img.getexif()
    for name, value in tags.items():
        exif[TAG_NAMES_TO_IDS[name]] = value
    img.save(img_path, exif=exif)

    return img_path


@pytest.fixture
def image_file(tmp_path):
    yield create_image_file(tmp_path, "image.jpg", tags={"ImageDescription": "A comment"})


class TestExifToolWrapper:
    @pytest.mark.parametrize(
        "with_common_args", (True, False), ids=("with-common-args", "without-common-args")
    )
    @mock.patch("subprocess.Popen")
    def test__pipe(self, Popen, with_common_args):
        """Test the `ExifToolWrapper._pipe` property."""
        Popen.return_value = sentinel = object()

        if with_common_args:
            common_args = ["-G"]
        else:
            common_args = None

        wrapper = ExifToolWrapper(common_args=common_args)

        assert wrapper._pipe is sentinel
        # test that pipe is only created once
        assert wrapper._pipe is sentinel

        Popen.assert_called_once()
        (popen_args,), _ = Popen.call_args
        if with_common_args:
            common_args_opt_idx_start = popen_args.index("-common_args") + 1
            common_args_opt_idx_end = common_args_opt_idx_start + len(common_args)

            assert popen_args[common_args_opt_idx_start:common_args_opt_idx_end] == common_args
        else:
            assert "-common_args" not in popen_args

    def test_process_json(self, image_file):
        """Test `ExifToolWrapper.process_json()`.

        This also tests `ExifToolWrapper.process()` and
        `ExifToolWrapper._encode_args`.
        """
        wrapper = ExifToolWrapper(common_args=["-G"])
        exifdata = wrapper.process_json(image_file, args=["-n"])
        assert exifdata["EXIF:ImageDescription"] == "A comment"

    @pytest.mark.parametrize("encoding", ("utf-8", "ascii"))
    def test_process_json_many(self, encoding, tmp_path):
        """Test `ExifToolWrapper.process_json_many()`"""
        images = [
            create_image_file(
                tmp_path, f"file{num}.jpg", tags={"ImageDescription": f"A comment #{num}"}
            )
            for num in range(1, 6)
        ]
        wrapper = ExifToolWrapper(common_args=["-G"])

        results = wrapper.process_json_many(*images, encoding=encoding)

        for num, exifdata in enumerate(results, start=1):
            assert exifdata["EXIF:ImageDescription"] == f"A comment #{num}"

    async def test_process_json_async(self, image_file):
        """Test `ExifToolWrapper.process_json_async()`.

        This also tests `ExifToolWrapper.process_many_json_async()`.
        """
        wrapper = ExifToolWrapper(common_args=["-G"])
        exifdata = await wrapper.process_json_async(image_file)
        assert exifdata["EXIF:ImageDescription"] == "A comment"

    async def test_process_json_many_async(self, tmp_path):
        """Test `ExifToolWrapper.process_json_many_async()`"""
        images = [
            create_image_file(
                tmp_path, f"file{num}.jpg", tags={"ImageDescription": f"A comment #{num}"}
            )
            for num in range(1, 6)
        ]
        wrapper = ExifToolWrapper(common_args=["-G"])

        results = await wrapper.process_json_many_async(*images)

        for num, exifdata in enumerate(results, start=1):
            assert exifdata["EXIF:ImageDescription"] == f"A comment #{num}"

    async def test_process_json_async_concurrently(self, tmp_path):
        """Test running `ExifToolWrapper.process_json_async()` concurrently."""
        images = [
            create_image_file(
                tmp_path, f"file{num}.jpg", tags={"ImageDescription": f"A comment #{num}"}
            )
            for num in range(1, 101)
        ]
        wrapper = ExifToolWrapper(common_args=["-G"])

        results = await asyncio.gather(*(wrapper.process_json_async(image) for image in images))

        for num, exifdata in enumerate(results, start=1):
            assert exifdata["EXIF:ImageDescription"] == f"A comment #{num}"
