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
base=${1:-http://127.0.0.1:8090}
base=${base%/}

read -p "Press Enter for Catalogue identity and navigation."
clear && curl -v --fail --silent --show-error "$base/" | jq .

read -p "Press Enter for Advertised conformance classes."
clear && curl -v --fail --silent --show-error "$base/conformance" | jq .

read -p "Press Enter for Static collection metadata, including datasets not loaded in this demo."
clear && curl -v --fail --silent --show-error "$base/collections" | jq .

read -p "Press Enter for NAIP's Colorado/Nebraska coverage and acquisition dates."
clear && curl -v --fail --silent --show-error "$base/collections/naip" | jq .

read -p "Press Enter for Two imagery tiles acquired in 2022."
clear && curl -v --fail --silent --show-error --get "$base/collections/naip/items" \
  --data-urlencode 'limit=2' \
  --data-urlencode 'bbox=-103,40,102,42' \
  --data-urlencode 'datetime=2022-01-01T00:00:00Z/2022-12-31T23:59:59Z' \
  | jq .

read -p "Press Enter for A real southwest-quarter NAIP tile near the Nebraska/Colorado border."
item=ne_m_4110264_sw_13_060_20220827
clear && curl -v --fail --silent --show-error "$base/collections/naip/items/$item" \
  | jq .

read -p "Press Enter to GET search combines collection and item identifiers."
clear && curl -v --fail --silent --show-error --get "$base/search" \
  --data-urlencode 'collections=naip' --data-urlencode "ids=$item" \
  | jq .

read -p "Press Enter to POST search uses the adapter's JSON-encoded string for intersects."
clear
jq -n '{collections: ["naip"], limit: 2,
  datetime: "2022-01-01T00:00:00Z/..",
  intersects: ({type: "Point", coordinates: [-102.09, 41.03]} | tojson)}' \
  | curl -v --fail --silent --show-error "$base/search" \
      --header 'Content-Type: application/json' --data @- \
  | jq .
