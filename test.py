import json

locations_file = open(f'location_packs/locations_ru.json')
all_locations = json.load(locations_file)
for pack in all_locations.keys():
    print(pack)