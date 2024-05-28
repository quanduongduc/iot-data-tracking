import json
import numpy as np
dest = "/home/dukwan/working/personal/data/weather"
sample_data = {
    "Date": "2024-05-13T23:40:20",
    "Latitude": 24.4667,
    "Longitude": 54.3667,
    "cld": "16.30000114440918",
    "dtr": 13.6000003815,
    "frs": 0,
    "pet": 8.1000003815,
    "pre": 1.3999999762,
    "tmn": 25.3000011444,
    "tmp": 32.1000022888,
    "tmx": 38.9000015259,
    "vap": 25.8000011444,
    "wet": 0.0,
}

locations = []
with open(
    "/home/dukwan/working/personal/fast-api-ecs/api/migrations/location_list.json",
    "r",
) as f:
    locations = json.load(f)

for location in locations:
    datas = [
        {
            key: (
                np.random.normal(loc=float(value))
                if key
                in [
                    "cld",
                    "dtr",
                    "frs",
                    "pet",
                    "pre",
                    "tmn",
                    "tmp",
                    "tmx",
                    "vap",
                    "wet",
                ]
                else value
            )
            for key, value in sample_data.items()
        }
        for _ in range(1000)
    ]
    
    with open(f"{dest}/{location}.json", "w") as f:
        json.dump(datas, f)
