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
base=${1:-http://127.0.0.1:8000}
base=${base%/}

# Catalogue identity and navigation.
curl --fail --silent --show-error "$base/" | jq '{id, title, links}'
# Advertised conformance classes.
curl --fail --silent --show-error "$base/conformance" | jq .
# Static collection metadata, including datasets not loaded in this demo.
curl --fail --silent --show-error "$base/collections" | jq '.collections[] | {id, description}'
# NAIP's Colorado/Nebraska coverage and acquisition dates.
curl --fail --silent --show-error "$base/collections/naip" | jq '{id, extent}'
# Two imagery tiles acquired in 2022. The adapter accepts repeated bbox parameters.
curl --fail --silent --show-error --get "$base/collections/naip/items" \
  --data-urlencode 'limit=2' \
  --data-urlencode 'bbox=-103' --data-urlencode 'bbox=40' \
  --data-urlencode 'bbox=-102' --data-urlencode 'bbox=42' \
  --data-urlencode 'datetime=2022-01-01T00:00:00Z/2022-12-31T23:59:59Z' \
  | jq '{type, features: [.features[] | {id, bbox, properties}]}'
# A real southwest-quarter NAIP tile near the Nebraska/Colorado border.
item=ne_m_4110264_sw_13_060_20220827
curl --fail --silent --show-error "$base/collections/naip/items/$item" \
  | jq '{id, collection, geometry, assets}'
# GET search combines collection and item identifiers.
curl --fail --silent --show-error --get "$base/search" \
  --data-urlencode 'collections=naip' --data-urlencode "ids=$item" \
  | jq '{type, ids: [.features[].id]}'
# POST search uses the adapter's JSON-encoded string for intersects.
jq -n '{collections: ["naip"], limit: 2,
  datetime: "2022-01-01T00:00:00Z/..",
  intersects: ({type: "Point", coordinates: [-102.09, 41.03]} | tojson)}' \
  | curl --fail --silent --show-error "$base/search" \
      --header 'Content-Type: application/json' --data-binary @- \
  | jq '{type, features: [.features[] | {id, properties}]}'
