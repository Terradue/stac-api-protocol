#!/usr/bin/env bash

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

set -euo pipefail
# Run from any directory; override the target with STAC_DEMO_DATA_DIR.
data_dir=${STAC_DEMO_DATA_DIR:-"$(dirname "${BASH_SOURCE[0]}")/data"}
base=https://raw.githubusercontent.com/developmentseed/labs-375-stac-geoparquet-backend/main/data
mkdir -p "$data_dir"
for filename in collections.json naip.parquet; do
  curl --fail --location --show-error "$base/$filename" --output "$data_dir/$filename"
done
