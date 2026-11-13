# Copyright 2026 Terradue
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import Mock, patch

import pytest

from stac_api_protocol.plugin_loader import load_dependency


def test_loads_callable_without_invoking_it() -> None:
    provider = Mock()
    entry = Mock()
    entry.load.return_value = provider
    with patch("stac_api_protocol.plugin_loader.entry_points", return_value=[entry]) as discover:
        assert load_dependency("item_service") is provider
    discover.assert_called_once_with(group="stacapi.service", name="item_service")
    entry.load.assert_called_once_with()
    provider.assert_not_called()


@pytest.mark.parametrize("count", [0, 2])
def test_rejects_missing_or_ambiguous_providers(count: int) -> None:
    entries = [Mock() for _ in range(count)]
    message = "Missing required dependency" if count == 0 else "Multiple implementations found for"
    with (
        patch("stac_api_protocol.plugin_loader.entry_points", return_value=entries),
        pytest.raises(RuntimeError, match=f"{message}: item_service"),
    ):
        load_dependency("item_service")
    for entry in entries:
        entry.load.assert_not_called()


@pytest.mark.parametrize("provider", [None, "not callable", 42])
def test_rejects_non_callable_provider(provider: object) -> None:
    entry = Mock()
    entry.load.return_value = provider
    with (
        patch("stac_api_protocol.plugin_loader.entry_points", return_value=[entry]),
        pytest.raises(RuntimeError, match="Dependency is not callable: item_service"),
    ):
        load_dependency("item_service")


def test_preserves_plugin_import_failure() -> None:
    entry = Mock()
    error = ImportError("plugin dependency unavailable")
    entry.load.side_effect = error
    with (
        patch("stac_api_protocol.plugin_loader.entry_points", return_value=[entry]),
        pytest.raises(ImportError) as raised,
    ):
        load_dependency("item_service")
    assert raised.value is error
