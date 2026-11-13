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

"""Import the adapter with an isolated provider instead of an installed plugin."""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from stac_api_protocol.stac_service import StacApiService

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType


@pytest.fixture
def service() -> Mock:
    """Provide a fresh service double constrained to the service interface."""
    return Mock(spec=StacApiService)


@pytest.fixture(scope="module")
def api() -> Iterator[ModuleType]:
    """Load routes without requiring a third-party entry point registration."""
    with patch("stac_api_protocol.plugin_loader.load_dependency", return_value=Mock()):
        module = importlib.import_module("stac_api_protocol.main")
    yield module
    sys.modules.pop("stac_api_protocol.main", None)
