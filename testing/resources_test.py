import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def _fetch_source_worker(data_dir: str, marker_dir: str) -> None:
    from pyku.resources import _fetch_source

    class Installer:
        def fetch(self, filename: str) -> str:
            marker_path = Path(marker_dir) / "active"
            overlap_path = Path(marker_dir) / "overlap"
            count_path = Path(marker_dir) / "count"

            if marker_path.exists():
                overlap_path.touch()

            marker_path.touch()
            time.sleep(0.1)
            marker_path.unlink(missing_ok=True)
            with count_path.open("a") as count_file:
                count_file.write(f"{filename}\n")
            return filename

    _fetch_source(Installer(), "shared.nc", Path(data_dir))


class TestResourceCaching(unittest.TestCase):
    def test_hostrada_caches_are_separate_in_either_order(self) -> None:
        import xarray as xr
        from pyku import resources

        source_stem = "tas_1hr_HOSTRADA-v1-0_BE_gn_1995010100-1995013123"
        loaders = [
            ("low", resources._get_low_res_hourly_tas_data),
            ("native", resources._get_hostrada_data),
        ]

        with tempfile.TemporaryDirectory() as temporary_dir:
            for order in (loaders, list(reversed(loaders))):
                data_dir = Path(temporary_dir) / order[0][0]
                data_dir.mkdir()
                xr.Dataset({"tas": ("x", [1.0, 2.0])}).to_zarr(
                    data_dir / f"{source_stem}_low_res.zarr",
                    consolidated=True,
                )
                xr.Dataset({"tas": ("x", [3.0, 4.0, 5.0])}).to_zarr(
                    data_dir / f"{source_stem}_native.zarr",
                    consolidated=True,
                )

                class Config:
                    def __init__(self, directory: Path) -> None:
                        self.directory = directory

                    def get(self, key: str) -> str:
                        return str(self.directory)

                with (
                    patch.object(
                        resources,
                        "PYKU_CONFIG",
                        Config(data_dir),
                    ),
                    patch("pooch.create", return_value=Mock()),
                ):
                    for resolution, loader in order:
                        with loader() as result:
                            expected_size = 2 if resolution == "low" else 3
                            self.assertEqual(result.sizes["x"], expected_size)

    def test_shared_source_lock_serializes_processes(self):
        from pyku.resources import _source_lock_path

        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir) / "data"
            marker_dir = Path(temporary_dir) / "markers"
            data_dir.mkdir()
            marker_dir.mkdir()

            context = multiprocessing.get_context("spawn")
            processes = [
                context.Process(
                    target=_fetch_source_worker,
                    args=(str(data_dir), str(marker_dir)),
                )
                for _ in range(2)
            ]

            for process in processes:
                process.start()
            for process in processes:
                process.join()

            self.assertEqual([p.exitcode for p in processes], [0, 0])
            self.assertFalse((marker_dir / "overlap").exists())
            self.assertEqual(
                len((marker_dir / "count").read_text().splitlines()),
                2,
            )
            self.assertEqual(
                _source_lock_path(data_dir, "shared.nc").name,
                "shared.nc.source.lock",
            )

    def test_zarr_is_published_after_successful_write(self):
        import xarray as xr
        from pyku.resources import _write_zarr_atomic

        with tempfile.TemporaryDirectory() as temporary_dir:
            zarr_path = Path(temporary_dir) / "dataset.zarr"
            dataset = xr.Dataset({"value": ("time", [1, 2])})

            _write_zarr_atomic(dataset, zarr_path, consolidated=True)

            with xr.open_zarr(zarr_path, consolidated=True) as result:
                self.assertEqual(result.value.values.tolist(), [1, 2])

    def test_failed_zarr_write_is_not_published(self):
        from pyku.resources import _write_zarr_atomic

        class FailingDataset:
            def to_zarr(self, path: Path, mode: str, **kwargs: object) -> None:
                path.mkdir()
                (path / "partial").touch()
                raise RuntimeError("conversion failed")

        with tempfile.TemporaryDirectory() as temporary_dir:
            zarr_path = Path(temporary_dir) / "dataset.zarr"

            with self.assertRaisesRegex(RuntimeError, "conversion failed"):
                _write_zarr_atomic(FailingDataset(), zarr_path)

            self.assertFalse(zarr_path.exists())
            self.assertEqual(
                list(Path(temporary_dir).glob(".dataset.zarr.*")),
                [],
            )

    def test_invalid_zarr_store_is_rejected(self):
        import numpy as np
        import xarray as xr

        from pyku.resources import _is_valid_zarr_store

        with tempfile.TemporaryDirectory() as temporary_dir:
            zarr_path = Path(temporary_dir) / "dataset.zarr"
            dataset = xr.Dataset(
                {
                    "lon": (("y", "x"), np.full((2, 2), np.nan)),
                    "lat": (("y", "x"), np.full((2, 2), np.nan)),
                }
            )
            dataset.to_zarr(zarr_path, consolidated=True)

            self.assertFalse(_is_valid_zarr_store(zarr_path))

    def test_empty_zarr_store_is_rejected(self):
        import xarray as xr

        from pyku.resources import _is_valid_zarr_store

        with tempfile.TemporaryDirectory() as temporary_dir:
            zarr_path = Path(temporary_dir) / "dataset.zarr"
            xr.Dataset().to_zarr(zarr_path, consolidated=True)

            self.assertFalse(_is_valid_zarr_store(zarr_path))


if __name__ == "__main__":
    unittest.main()
