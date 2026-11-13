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

"""Load service providers registered through Python entry points."""

from collections.abc import Callable
from importlib.metadata import entry_points


def load_dependency(name: str) -> Callable[..., object]:
    """Load the unique callable provider registered under the given name.

    Raises:
        RuntimeError: If no provider, multiple providers, or a non-callable
            provider is registered.
    """
    matches = entry_points(
        group="stacapi.service",
        name=name,
    )

    if not matches:
        raise RuntimeError(f"Missing required dependency: {name}")

    if len(matches) > 1:
        raise RuntimeError(f"Multiple implementations found for: {name}")

    provider: object = next(iter(matches)).load()
    if not callable(provider):
        raise RuntimeError(f"Dependency is not callable: {name}")
    return provider
