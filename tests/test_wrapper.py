from unittest import mock

import pytest
from PIL import ExifTags, Image

from exiftool_wrapper.wrapper import ExifToolWrapper

TAG_NAMES_TO_IDS = {value: key for key, value in ExifTags.TAGS.items()}


@pytest.fixture
def image_file(tmp_path):
    img_path = tmp_path / "image.jpg"
    img = Image.new("RGB", (32, 32))
    exif = img.getexif()
    exif[TAG_NAMES_TO_IDS["ImageDescription"]] = "A comment"
    img.save(img_path, exif=exif)

    yield img_path


class TestExifToolWrapper:
    @pytest.mark.parametrize("with_common_args", (True, False))
    @mock.patch("subprocess.Popen")
    def test_pipe(self, Popen, with_common_args):
        """Test the `ExifToolWrapper.pipe` property."""
        Popen.return_value = sentinel = object()

        if with_common_args:
            common_args = ["-G"]
        else:
            common_args = None

        wrapper = ExifToolWrapper(common_args=common_args)

        assert wrapper.pipe == sentinel
        # test that pipe is only created once
        assert wrapper.pipe == sentinel

        Popen.assert_called_once()
        (popen_args,), kwargs = Popen.call_args
        if with_common_args:
            common_args_opt_idx_start = popen_args.index("-common_args") + 1
            common_args_opt_idx_end = common_args_opt_idx_start + len(common_args)

            assert popen_args[common_args_opt_idx_start:common_args_opt_idx_end] == common_args
        else:
            assert "-common_args" not in popen_args

    def test_process_json(self, image_file):
        """Test `ExifToolWrapper.process_json()`.

        This also tests `ExifToolWrapper.process()`,
        `ExifToolWrapper.process_many_json()` and
        `ExifToolWrapper._encode_args`.
        """
        wrapper = ExifToolWrapper(common_args=["-G"])
        exifdata = wrapper.process_json(image_file)
        assert exifdata["EXIF:ImageDescription"] == "A comment"

    async def test_process_json_async(self, image_file):
        """Test `ExifToolWrapper.process_json_async()`.

        This also tests `ExifToolWrapper.process_many_json_async()`.
        """
        wrapper = ExifToolWrapper(common_args=["-G"])
        exifdata = await wrapper.process_json_async(image_file)
        assert exifdata["EXIF:ImageDescription"] == "A comment"
