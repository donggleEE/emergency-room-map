import json
import os

files = [
    "data/korea_sido.geojson",
    "data/korea_sigungu.geojson",
]

for path in files:
    print("\n" + "=" * 60)
    print("파일:", path)

    if not os.path.exists(path):
        print("파일 없음")
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("최상위 type:", data.get("type"))
    print("최상위 key:", list(data.keys()))

    features = data.get("features", [])
    print("features 개수:", len(features))

    if len(features) == 0:
        print("features가 비어 있음")
        continue

    first = features[0]

    print("첫 번째 feature key:", list(first.keys()))
    print("geometry type:", first.get("geometry", {}).get("type"))

    props = first.get("properties", {})
    print("properties key 목록:")
    print(list(props.keys()))

    print("properties 실제 값:")
    print(props)

    print("\n앞에서 5개 행정구역 이름 후보:")
    for i, feature in enumerate(features[:5]):
        props = feature.get("properties", {})
        print(f"{i + 1}번째:", props)
        